from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.contracts.models import (
    AccessorySpec,
    CustomerQueryRaw,
    DimensionsSpec,
    FieldEnvelope,
    FieldStatus,
    LoopSpec,
    PrintingSpec,
    StructuredSpec,
)
from app.normalization.extractor import normalize_customer_query, raw_query_from_text
from app.pipeline import run_pipeline
from app.rules import generate_u_panel_bom
from app.validation import validate_bom


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def fe(value, unit=None, status=FieldStatus.PROVIDED):
    return FieldEnvelope(value=value, unit=unit, status=status, confidence=0.9, source_text=None, source="test")


def ns(value=None, unit=None):
    return FieldEnvelope(value=value, unit=unit, status=FieldStatus.NOT_SPECIFIED, confidence=1.0, source_text=None, source=None)


def spec_from_record(record: dict, idx: int) -> StructuredSpec:
    return StructuredSpec(
        spec_id=f"hist-{idx}",
        source_query_id=f"hist-query-{idx}",
        customer=ns(record.get("customer")),
        ref_no=ns(record.get("ref_no")),
        bag_type=fe("u_panel"),
        dimensions=DimensionsSpec(
            int_L=fe(record["int_L"], "cm"),
            int_W=fe(record["int_W"], "cm"),
            int_H=fe(record["int_H"], "cm"),
            ext_L=fe(record["ext_L"], "cm"),
            ext_W=fe(record["ext_W"], "cm"),
            ext_H=fe(record["ext_H"], "cm"),
        ),
        swl_kg=fe(record["swl_kg"], "kg"),
        sf=fe(record["sf"]),
        bag_weight_target_g=ns(record.get("bag_weight_target_g"), "g"),
        fabric_color=fe(record.get("fabric_color") or "WHITE"),
        body_laminated=fe(bool(record.get("body_laminated"))),
        double_layer=fe(bool(record.get("double_layer"))),
        top_type=fe(record.get("top_type") or "OPEN_TOP"),
        bottom_type=fe("IRIS" if record.get("ds_closure") == "IRIS" else ("DISCHARGE_SPOUT" if record.get("has_ds_spout") else "FLAT_BOTTOM")),
        loop=LoopSpec(
            loop_family=fe("corner_loop"),
            loop_qty=fe(record.get("loop_qty") or 4),
            loop_width_mm=fe(record.get("loop_width_mm") or 50, "mm"),
            loop_LL_cm=fe(record.get("loop_LL_cm") or 70, "cm"),
            loop_SL_cm=fe(record.get("loop_SL_cm") or 50, "cm"),
            loop_color=fe(record.get("loop_color") or "WHITE"),
            free_height_cm=ns(None, "cm"),
        ),
        accessories=AccessorySpec(
            has_fs_spout=fe(bool(record.get("has_fs_spout"))),
            fs_spout_dia_cm=fe(record.get("fs_spout_w_cm") or 40, "cm"),
            fs_spout_h_cm=fe(record.get("fs_spout_h_cm") or 50, "cm"),
            has_ds_spout=fe(bool(record.get("has_ds_spout"))),
            ds_spout_dia_cm=fe(record.get("ds_spout_w_cm") or 35, "cm"),
            ds_spout_h_cm=fe(record.get("ds_spout_h_cm") or 50, "cm"),
            ds_closure=fe(record.get("ds_closure") or "TIE"),
            has_baffle=fe(False),
            has_liner=fe(bool(record.get("has_liner"))),
            liner_micron=fe(record.get("liner_micron") or 70, "micron"),
            has_doc_pocket=fe(bool(record.get("has_doc_pocket"))),
            doc_pocket_size=fe(record.get("doc_pocket_size") or "A4"),
            has_ddp=fe(bool(record.get("has_ddp"))),
            has_stevedore=fe(bool(record.get("has_stevedore"))),
        ),
        printing=PrintingSpec(
            printing_sides=fe(record.get("printing_sides") or 0),
            printing_colors=fe(record.get("printing_colors") or 0),
            printing_color_names=ns([]),
        ),
        notes=[],
    )


class UPanelPipelineTests(unittest.TestCase):
    def test_no_doc_pocket_without_customer_trigger(self):
        raw = raw_query_from_text("90x90x100 U+2 panel SWL 1000 kg SF 5 flat bottom no printing")
        spec = normalize_customer_query(raw).structured_spec
        bom = generate_u_panel_bom(spec)
        names = [c.canonical_name for c in bom.components]
        self.assertNotIn("DOC POCKET", names)
        self.assertEqual(validate_bom(bom).hard_failures, [])

    def test_doc_pocket_with_customer_trigger(self):
        package = run_pipeline("85x85x110 U+2 panel SWL 1250 kg SF 5 top panel doc pocket no printing", with_retrieval=False)
        names = [c.canonical_name for c in package.final_bom.components]
        self.assertIn("DOC POCKET", names)
        self.assertFalse(package.validation_report.hard_failures)

    def test_twenty_historical_u_panel_specs_generate_valid_boms(self):
        records = json.loads((PROJECT_ROOT / "bom_extracted_dataset.json").read_text(encoding="utf-8"))
        u_panel = [
            r for r in records
            if r.get("bag_type") == "u_panel" and r.get("swl_kg") and r.get("sf") and r.get("int_L") and not r.get("has_baffle")
        ][:20]
        self.assertEqual(len(u_panel), 20)
        failures = []
        for idx, record in enumerate(u_panel):
            spec = spec_from_record(record, idx)
            bom = generate_u_panel_bom(spec)
            report = validate_bom(bom)
            if report.hard_failures:
                failures.append((record.get("source_file"), [f.code for f in report.hard_failures]))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
