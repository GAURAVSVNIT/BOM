"""Dataset rows (03_DATASET/adapter_{a,b}/*.jsonl) -> chat-format SFT examples.

Torch-free. `build_hf_dataset` imports `datasets` lazily so the rest is usable
for inspection and unit tests without any ML stack.

Row shapes produced by the data pipeline
----------------------------------------
adapter A : {system:str, input:str,  output:dict(OrderSpec), style, id, fingerprint, split, meta}
adapter B : {system:str, input:dict(order_spec/retrieved/envelope),
             output:dict(BuildSpec)  OR  {build_spec, clarification},
             row_type, id, fingerprint, split, meta}

Each becomes a 3-message chat: system / user / assistant, where the assistant
message is the canonical compact JSON of `output`. Completion-only loss masks
everything up to `cfg.data.response_template`.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterator

from .paths import adapter_jsonl

# a compact, stable JSON encoding — identical to what grammar-constrained
# decoding emits at serve time, so train/serve strings match.
def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build the dataset first "
            f"(03_DATASET/build/06_adapter_a.py / 07_adapter_b.py)."
        )
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_rows(adapter: str, split: str, limit: int | None = None) -> list[dict]:
    rows = _read_jsonl(adapter_jsonl(adapter, split))
    return rows[:limit] if limit else rows


def _user_content(row: dict, adapter: str) -> str:
    if adapter == "a":
        return row["input"]                       # raw enquiry text
    # adapter B: the model reads a structured prompt. Keep it compact but
    # labelled so the sections are legible to the model.
    inp = row["input"]
    parts = []
    if "order_spec" in inp:
        parts.append("ORDER_SPEC:\n" + dumps(inp["order_spec"]))
    if inp.get("retrieved"):
        parts.append("RETRIEVED_NEIGHBOURS:\n" + dumps(inp["retrieved"]))
    if "current_build_spec" in inp:
        parts.append("CURRENT_BUILD_SPEC:\n" + dumps(inp["current_build_spec"]))
    if "weight_feedback" in inp:
        parts.append("WEIGHT_FEEDBACK:\n" + dumps(inp["weight_feedback"]))
    if "envelope" in inp:
        parts.append("RULE_ENVELOPE:\n" + dumps(inp["envelope"]))
    return "\n\n".join(parts)


def to_messages(row: dict, adapter: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": row["system"]},
            {"role": "user", "content": _user_content(row, adapter)},
            {"role": "assistant", "content": dumps(row["output"])},
        ],
        "meta": {"id": row.get("id"), "row_type": row.get("row_type", row.get("style")),
                 "split": row.get("split")},
    }


def iter_examples(adapter: str, split: str, limit: int | None = None) -> Iterator[dict]:
    for row in load_rows(adapter, split, limit):
        yield to_messages(row, adapter)


def render_plain(example: dict) -> str:
    """Chat-template-free rendering for eyeballing without a tokenizer."""
    out = []
    for m in example["messages"]:
        out.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
    return "\n".join(out)


def apply_template(tokenizer, messages, add_generation_prompt=False,
                   enable_thinking=False):
    """Render chat turns. `enable_thinking` is only honoured by Qwen3 thinking
    templates; other templates ignore the kwarg."""
    try:
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=add_generation_prompt,
            enable_thinking=enable_thinking)
    except TypeError:                       # template doesn't take enable_thinking
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=add_generation_prompt)


def build_chat_dataset(adapter: str, split: str, limit: int | None = None):
    """A `datasets.Dataset` with a `messages` column (list[{role,content}]).
    trl >= 1.x auto-detects this 'conversational' form, applies the tokenizer
    chat template itself, and (with assistant_only_loss) masks the prompt."""
    from datasets import Dataset
    exs = list(iter_examples(adapter, split, limit))
    return Dataset.from_dict({"messages": [e["messages"] for e in exs],
                              "row_type": [e["meta"]["row_type"] for e in exs]})


def build_hf_dataset(adapter: str, split: str, tokenizer, limit: int | None = None,
                     enable_thinking: bool = False):
    """A `datasets.Dataset` with a single pre-rendered `text` column — used by
    the Unsloth backend / trl versions that want plain text."""
    from datasets import Dataset
    exs = list(iter_examples(adapter, split, limit))
    texts = [apply_template(tokenizer, e["messages"], enable_thinking=enable_thinking)
             for e in exs]
    return Dataset.from_dict({"text": texts,
                              "row_type": [e["meta"]["row_type"] for e in exs]})


def stats(adapter: str) -> dict:
    out = {}
    for split in ("train", "val", "test"):
        try:
            rows = load_rows(adapter, split)
        except FileNotFoundError:
            continue
        from collections import Counter
        rt = Counter(r.get("row_type", r.get("style", "?")) for r in rows)
        out[split] = {"n": len(rows), "by_type": dict(rt)}
    return out
