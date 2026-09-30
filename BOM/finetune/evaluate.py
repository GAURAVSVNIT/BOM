"""Structural evaluation of a fine-tuned BOM adapter against the held-out val set.

This does not just eyeball generated text — it runs the exact same hard-constraint
checks the deterministic pipeline is graded on (rules/hard_constraints.json:
canonical component vocabulary + mandatory-by-bag-type), plus a comparison against
the ground-truth historical BOM for each val record. A model that "sounds right"
but violates these is not usable behind synthesize_with_retry's llm callable.

Usage:
    python evaluate.py --base-model ../model_weights --adapter-dir runs/qwen_bom_lora
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer

from bom_csv import BomCsvError, component_weight_sum, parse_bom_csv

THIS_DIR = Path(__file__).resolve().parent
BOM_ROOT = THIS_DIR.parent

MODEL_CLASSES = {
    "image-text-to-text": AutoModelForImageTextToText,
    "causal-lm": AutoModelForCausalLM,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-model", default=str(BOM_ROOT / "model_weights"))
    p.add_argument("--model-class", choices=list(MODEL_CLASSES), default="image-text-to-text")
    p.add_argument("--adapter-dir", required=True, help="output-dir passed to train_qwen_bom.py")
    p.add_argument("--val-file", default=str(THIS_DIR / "data" / "val.jsonl"))
    p.add_argument("--max-new-tokens", type=int, default=512)
    p.add_argument("--limit", type=int, default=None, help="only evaluate the first N val examples")
    p.add_argument("--report-out", default=str(THIS_DIR / "data" / "eval_report.json"))
    return p.parse_args()


def load_rulebook() -> dict:
    return json.loads((BOM_ROOT / "rules" / "hard_constraints.json").read_text(encoding="utf-8"))


def load_model(args: argparse.Namespace):
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = MODEL_CLASSES[args.model_class].from_pretrained(
        args.base_model, dtype=torch.bfloat16, device_map="auto", trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base, args.adapter_dir)
    model.eval()
    return model, tokenizer


@torch.inference_mode()
def generate(model, tokenizer, system: str, user: str, max_new_tokens: int) -> str:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.pad_token_id,
    )
    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def score_example(generated_text: str, meta: dict, rulebook: dict) -> dict:
    result: dict = {"source_file": meta.get("source_file"), "source_sheet": meta.get("source_sheet"), "bag_type": meta.get("bag_type")}

    try:
        components, grand_total = parse_bom_csv(generated_text)
    except BomCsvError as exc:
        result.update(parse_ok=False, parse_error=str(exc))
        return result

    canonical = set(rulebook["canonical_components"])
    names = [c["COMPONENT"] for c in components]
    bad_names = sorted({n for n in names if n not in canonical})

    mandatory = set(rulebook["mandatory_by_bag_type"].get(meta.get("bag_type"), []))
    missing_mandatory = sorted(mandatory - set(names))

    row_sum = component_weight_sum(components)
    weight_formula_ok = abs(row_sum - grand_total) <= rulebook["weight_formula_tolerance_g"]["generated"] * 10  # generous: model output, not exact rule-engine arithmetic

    gt_total = meta.get("ground_truth_total_g")
    weight_rel_error = abs(grand_total - gt_total) / gt_total if gt_total else None

    gt_components = set(meta.get("ground_truth_components", []))
    component_set_match = set(names) == gt_components

    result.update(
        parse_ok=True,
        non_canonical_components=bad_names,
        missing_mandatory_components=missing_mandatory,
        hard_constraints_pass=not bad_names and not missing_mandatory,
        weight_formula_ok=weight_formula_ok,
        generated_total_g=grand_total,
        ground_truth_total_g=gt_total,
        weight_relative_error=weight_rel_error,
        component_set_match=component_set_match,
    )
    return result


def main() -> None:
    args = parse_args()
    rulebook = load_rulebook()
    model, tokenizer = load_model(args)

    val_records = [json.loads(line) for line in Path(args.val_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        val_records = val_records[: args.limit]

    results = []
    for i, rec in enumerate(val_records):
        system_msg, user_msg = rec["messages"][0]["content"], rec["messages"][1]["content"]
        generated = generate(model, tokenizer, system_msg, user_msg, args.max_new_tokens)
        result = score_example(generated, rec["meta"], rulebook)
        result["generated_text"] = generated
        results.append(result)
        status = "OK" if result.get("hard_constraints_pass") else "FAIL"
        print(f"[{i + 1}/{len(val_records)}] {status} {rec['meta'].get('source_file')}")

    n = len(results)
    parse_ok = [r for r in results if r["parse_ok"]]
    summary = {
        "n_examples": n,
        "parse_success_rate": len(parse_ok) / n if n else 0.0,
        "hard_constraints_pass_rate": sum(r.get("hard_constraints_pass", False) for r in parse_ok) / n if n else 0.0,
        "component_set_exact_match_rate": sum(r.get("component_set_match", False) for r in parse_ok) / n if n else 0.0,
        "mean_weight_relative_error_pct": (
            statistics.mean(r["weight_relative_error"] for r in parse_ok if r.get("weight_relative_error") is not None) * 100
            if any(r.get("weight_relative_error") is not None for r in parse_ok)
            else None
        ),
        "weight_within_5pct_rate": (
            sum(1 for r in parse_ok if r.get("weight_relative_error") is not None and r["weight_relative_error"] <= 0.05) / n if n else 0.0
        ),
    }

    print("\n=== summary ===")
    print(json.dumps(summary, indent=2))

    Path(args.report_out).write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    print(f"\nfull report written to {args.report_out}")


if __name__ == "__main__":
    main()
