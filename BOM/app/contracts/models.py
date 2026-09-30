from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class FieldStatus(str, Enum):
    PROVIDED = "provided"
    INFERRED = "inferred"
    MISSING = "missing"
    NOT_SPECIFIED = "not_specified"
    INAPPLICABLE = "inapplicable"


class BagType(str, Enum):
    U_PANEL = "u_panel"
    CIRCULAR = "circular"
    FOUR_PANEL = "four_panel"
    FOUR_PANEL_BAFFLE = "four_panel_baffle"
    TWO_PANEL = "two_panel"
    SINGLE_LOOP = "single_loop"
    TWO_LOOP = "two_loop"
    TUBULAR = "tubular"
    OMEGA = "omega"
    PLATEN = "platen"
    BOX = "box"
    TUNNEL = "tunnel"
    CONTAINER = "container"
    CONDUCTIVE = "conductive"


class TopType(str, Enum):
    OPEN_TOP = "OPEN_TOP"
    TOP_PANEL = "TOP_PANEL"
    SKIRT = "SKIRT"
    DUFFLE = "DUFFLE"
    TOP_FLAP = "TOP_FLAP"


class BottomType(str, Enum):
    FLAT_BOTTOM = "FLAT_BOTTOM"
    CLOSED_BOTTOM = "CLOSED_BOTTOM"
    DISCHARGE_SPOUT = "DISCHARGE_SPOUT"
    IRIS = "IRIS"
    PETAL = "PETAL"


class LoopFamily(str, Enum):
    CORNER_LOOP = "corner_loop"
    CROSS_CORNER_LOOP = "cross_corner_loop"
    FULL_BODY_LOOP = "full_body_loop"
    SINGLE_LOOP = "single_loop"
    TWO_LOOP = "two_loop"
    NONE = "none"


class Lamination(str, Enum):
    LAMINATED = "LAMINATED"
    UNLAMINATED = "UNLAMINATED"
    PP = "PP"
    LDPE = "LDPE"
    BSL = "BSL"


class CanonicalComponent(str, Enum):
    BODY_PANEL = "BODY PANEL"
    SIDE_PANEL = "SIDE PANEL"
    BOTTOM_PANEL = "BOTTOM PANEL"
    TOP_PANEL = "TOP PANEL"
    TOP_FLAP = "TOP FLAP"
    SKIRT = "SKIRT"
    FILLING_SPOUT = "FILLING SPOUT"
    DISCHARGE_SPOUT = "DISCHARGE SPOUT"
    BAFFLE = "BAFFLE"
    DS_FLAP = "DS FLAP"
    DS_PATCH = "DS PATCH"
    LINER = "LINER"
    CORNER_LOOP = "CORNER LOOP"
    FULL_BODY_LOOP = "FULL BODY LOOP"
    STEVEDORE_LOOP = "STEVEDORE LOOP"
    FS_TIE = "FS TIE"
    DS_TIE = "DS TIE"
    PETAL_TIE = "PETAL TIE"
    TUCKING_TIE = "TUCKING TIE"
    DDP = "DDP"
    DOC_POCKET = "DOC POCKET"
    LOOP_PROTECTOR = "LOOP PROTECTOR"
    TOP_BAND = "TOP BAND"
    BELLY_BAND = "BELLY BAND"
    TABBING = "TABBING"
    STITCHING = "STITCHING"
    PRINTING = "PRINTING"
    LABEL = "LABEL"


class ValidationDecision(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    RETRY = "retry"
    FALLBACK_RULE_ENGINE = "fallback_rule_engine"
    REJECT = "reject"


class FieldEnvelope(StrictModel):
    value: Any = None
    unit: str | None = None
    status: FieldStatus
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: str | None = None
    source: str | None = None


class Attachment(StrictModel):
    attachment_id: str
    kind: Literal["image", "pdf", "xlsx", "csv", "other"]
    path: str
    ocr_text: str | None = None


class CustomerQueryRaw(StrictModel):
    query_id: str
    language_hint: Literal["hi", "en", "mixed", "unknown"] = "unknown"
    raw_text: str
    attachments: list[Attachment] = Field(default_factory=list)
    received_at: datetime


class DimensionsSpec(StrictModel):
    int_L: FieldEnvelope
    int_W: FieldEnvelope
    int_H: FieldEnvelope
    ext_L: FieldEnvelope
    ext_W: FieldEnvelope
    ext_H: FieldEnvelope


class LoopSpec(StrictModel):
    loop_family: FieldEnvelope
    loop_qty: FieldEnvelope
    loop_width_mm: FieldEnvelope
    loop_LL_cm: FieldEnvelope
    loop_SL_cm: FieldEnvelope
    loop_color: FieldEnvelope
    free_height_cm: FieldEnvelope


class AccessorySpec(StrictModel):
    has_fs_spout: FieldEnvelope
    fs_spout_dia_cm: FieldEnvelope
    fs_spout_h_cm: FieldEnvelope
    has_ds_spout: FieldEnvelope
    ds_spout_dia_cm: FieldEnvelope
    ds_spout_h_cm: FieldEnvelope
    ds_closure: FieldEnvelope
    has_baffle: FieldEnvelope
    has_liner: FieldEnvelope
    liner_micron: FieldEnvelope
    has_doc_pocket: FieldEnvelope
    doc_pocket_size: FieldEnvelope
    has_ddp: FieldEnvelope
    has_stevedore: FieldEnvelope


class PrintingSpec(StrictModel):
    printing_sides: FieldEnvelope
    printing_colors: FieldEnvelope
    printing_color_names: FieldEnvelope


class StructuredSpec(StrictModel):
    spec_id: str
    source_query_id: str
    customer: FieldEnvelope
    ref_no: FieldEnvelope
    bag_type: FieldEnvelope
    dimensions: DimensionsSpec
    swl_kg: FieldEnvelope
    sf: FieldEnvelope
    bag_weight_target_g: FieldEnvelope
    fabric_color: FieldEnvelope
    body_laminated: FieldEnvelope
    double_layer: FieldEnvelope
    top_type: FieldEnvelope
    bottom_type: FieldEnvelope
    loop: LoopSpec
    accessories: AccessorySpec
    printing: PrintingSpec
    notes: list[str] = Field(default_factory=list)


class BOMComponent(StrictModel):
    sr: int
    canonical_name: CanonicalComponent
    original_name: str | None = None
    gsm_area: float | None = None
    gsm_per_m: float | None = None
    lami_ul: Lamination | None = None
    color: str | None = None
    width_cm: float | None = None
    cut_cm: float | None = None
    qty: float = 1
    weight_g: float
    remark: str | None = None
    source: Literal["rule_engine", "retrieval", "llm", "historical"] = "rule_engine"


class Assumption(StrictModel):
    id: str
    field: str
    assumption: str
    basis: str


class RuleHit(StrictModel):
    rule_id: str
    rule_level: Literal["hard_constraint", "default_preference", "fallback_heuristic"]
    component: str | None = None


class PhysicalBOM(StrictModel):
    bom_id: str
    source: Literal["rule_engine", "llm_synthesis", "fallback_rule_engine", "historical"]
    source_spec_id: str
    source_file: str | None = None
    source_sheet: str | None = None
    customer: str | None = None
    ref_no: str | None = None
    bag_type: BagType
    swl_kg: float
    sf: float
    ext_L: float
    ext_W: float
    ext_H: float
    int_L: float
    int_W: float
    int_H: float
    bag_weight_target_g: float | None = None
    bag_weight_actual_g: float
    computed_total_g: float
    components: list[BOMComponent]
    candidate_optional_components: list[BOMComponent] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    rule_hits: list[RuleHit] = Field(default_factory=list)
    constraint_inputs: dict[str, Any] = Field(default_factory=dict)


class RetrievedBOM(StrictModel):
    retrieval_id: str
    source_file: str
    source_sheet: str
    record_index: int
    score_total: float
    score_breakdown: dict[str, float]
    why_matched: list[str]
    structured_spec_snapshot: dict[str, Any]
    component_list: list[dict[str, Any]]
    bag_weight_target_g: float | None = None
    bag_weight_actual_g: float | None = None
    data_warnings: list[str] = Field(default_factory=list)


class ValidationIssue(StrictModel):
    code: str
    path: str
    message: str
    allowed_values: list[Any] | None = None
    actual_value: Any = None
    reference_value: Any = None


class ValidationReport(StrictModel):
    schema_pass: bool
    hard_failures: list[ValidationIssue] = Field(default_factory=list)
    soft_warnings: list[ValidationIssue] = Field(default_factory=list)
    retriable: bool
    error_context_for_llm: dict[str, Any] = Field(default_factory=dict)
    final_decision: ValidationDecision


class AuditTrail(StrictModel):
    run_id: str
    raw_query: dict[str, Any]
    structured_spec: dict[str, Any]
    normalization_changes: list[dict[str, Any]]
    rule_engine_bom: dict[str, Any] | None = None
    rule_hits: list[dict[str, Any]] = Field(default_factory=list)
    retrieved_boms: list[dict[str, Any]] = Field(default_factory=list)
    llm_prompt_version: str | None = None
    llm_raw_output: dict[str, Any] | None = None
    validation_reports: list[dict[str, Any]] = Field(default_factory=list)
    retry_count: int = 0
    final_bom: dict[str, Any] | None = None
    final_pass_fail: Literal["pass", "pass_with_warnings", "fallback", "reject"] | None = None
    created_at: datetime


class FinalBOMPackage(StrictModel):
    package_id: str
    final_bom: PhysicalBOM
    validation_report: ValidationReport
    audit_trail_path: str
    csv_path: str
    xlsx_path: str
    summary: dict[str, Any]
    provenance: dict[str, Any]
