"""Serving with vLLM + grammar-constrained JSON (plan §9.3).

Entry points
------------
  main()       launch the OpenAI-compatible vLLM server with both LoRA adapters
               hot ("a" and "b") and guided decoding on. Used by slurm/serve.sbatch.
  LocalEngine  in-process vLLM.LLM for offline batch generation (no server) —
               used by bomft.evaluate.
  HttpClient   tiny stdlib client for a running server — used by bom_agent/ and by
               evaluate with --server. No `openai` package needed.
"""
from __future__ import annotations
import json
import os
import sys
import urllib.request
from pathlib import Path

from .config import Config, load_config
from .paths import base_model_path, run_dir
from .schema import guided_json


# ── locate a trained adapter ───────────────────────────────────────────
def adapter_path(adapter: str) -> Path:
    """Directory that holds the PEFT files (adapter_config.json + weights) for
    {a,b}: <run>/adapter, found via runs/adapter_x/latest[.txt] or newest run.
    Also accepts $BOM_ADAPTER_A_DIR / $BOM_ADAPTER_B_DIR pointing straight at a run."""
    import os
    direct = os.environ.get(f"BOM_ADAPTER_{adapter.upper()}_DIR")
    if direct:
        p = Path(direct)
        return p / "adapter" if (p / "adapter").exists() else p
    base = run_dir() / f"adapter_{adapter}"
    for cand in (base / "latest" / "adapter",):
        if cand.exists():
            return cand
    txt = base / "latest.txt"
    if txt.exists():
        p = Path(txt.read_text().strip())
        return p / "adapter" if (p / "adapter").exists() else p
    stamps = sorted(d for d in base.glob("*/adapter") if d.is_dir())
    if stamps:
        return stamps[-1]
    raise FileNotFoundError(
        f"no trained adapter '{adapter}' under {base}. Run training first, "
        f"or set BOM_ADAPTER_{adapter.upper()}_DIR.")


# ── OpenAI-compatible server launch ────────────────────────────────────
def vllm_serve_argv(cfg: Config) -> list[str]:
    model = str(base_model_path(cfg.model.name))
    argv = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--served-model-name", "bom-base",
        "--host", cfg.serve.host,
        "--port", str(cfg.serve.port),
        "--dtype", cfg.serve.dtype,
        "--max-model-len", str(cfg.serve.max_model_len),
        "--gpu-memory-utilization", str(cfg.serve.gpu_memory_utilization),
        "--guided-decoding-backend", cfg.serve.guided_decoding_backend,
    ]
    if cfg.serve.enable_lora:
        argv += [
            "--enable-lora",
            "--max-loras", str(cfg.serve.max_loras),
            "--max-lora-rank", str(cfg.serve.max_lora_rank),
            "--lora-modules",
            f"a={adapter_path('a')}",
            f"b={adapter_path('b')}",
        ]
    return argv


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser("bomft.serve")
    ap.add_argument("--config", default=str(Path(__file__).parents[1] / "configs" / "serve.yaml"))
    ap.add_argument("--print-cmd", action="store_true", help="print the vLLM command and exit")
    ap.add_argument("overrides", nargs="*")
    a = ap.parse_args(argv)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    cfg = load_config(a.config, a.overrides)
    cmd = vllm_serve_argv(cfg)
    print("[bomft.serve]", " ".join(cmd))
    if a.print_cmd:
        return 0
    from .preflight import assert_gpu_ok
    assert_gpu_ok(min_free_gb=20)
    os.execv(cmd[0], cmd)   # replace this process with the server


# ── in-process offline engine ─────────────────────────────────────────
class LocalEngine:
    def __init__(self, cfg: Config):
        from vllm import LLM
        self.cfg = cfg
        self.llm = LLM(
            model=str(base_model_path(cfg.model.name)),
            dtype=cfg.serve.dtype,
            max_model_len=cfg.serve.max_model_len,
            gpu_memory_utilization=cfg.serve.gpu_memory_utilization,
            enable_lora=True,
            max_loras=cfg.serve.max_loras,
            max_lora_rank=cfg.serve.max_lora_rank,
        )   # guided-decoding backend is selected per-request via GuidedDecodingParams
        self.tok = self.llm.get_tokenizer()

    def generate(self, adapter: str, chats: list[list[dict]],
                 max_tokens: int = 1536, temperature: float = 0.0) -> list[str]:
        from vllm import SamplingParams
        from vllm.lora.request import LoRARequest
        try:
            from vllm.sampling_params import GuidedDecodingParams
            guided = GuidedDecodingParams(json=guided_json(adapter))
            sp = SamplingParams(temperature=temperature, max_tokens=max_tokens,
                                guided_decoding=guided)
        except Exception:                       # older vLLM
            sp = SamplingParams(temperature=temperature, max_tokens=max_tokens)
        from .data import apply_template
        et = getattr(self.cfg.model, "enable_thinking", False)
        prompts = [apply_template(self.tok, c, add_generation_prompt=True,
                                  enable_thinking=et) for c in chats]
        lreq = LoRARequest(adapter, 1 if adapter == "a" else 2,
                           str(adapter_path(adapter)))
        outs = self.llm.generate(prompts, sp, lora_request=lreq)
        return [o.outputs[0].text for o in outs]


# ── HTTP client for a running server ──────────────────────────────────
class HttpClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 120):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, adapter: str, system: str, user: str,
                 max_tokens: int = 1536, temperature: float = 0.0) -> str:
        body = {
            "model": adapter,           # the --lora-modules name
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "guided_json": guided_json(adapter),           # vLLM top-level
            "extra_body": {"guided_json": guided_json(adapter)},
            # Qwen3 thinking models: force it off so the reply is pure JSON.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        req = urllib.request.Request(
            f"{self.base}/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            resp = json.loads(r.read())
        return resp["choices"][0]["message"]["content"]

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base}/health", timeout=5) as r:
                return r.status == 200
        except Exception:
            return False


if __name__ == "__main__":
    raise SystemExit(main())
