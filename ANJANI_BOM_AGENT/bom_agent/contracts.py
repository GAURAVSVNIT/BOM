"""Data contracts (plan §4). Light dataclasses, not Pydantic — enough to type the
pipeline and serialise. The `state` machine on OrderSpec makes "the customer did
not say" a first-class value so hallucination stays measurable (plan §4.1).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

STATES = ("provided", "not_specified", "derived", "repaired")


@dataclass
class Field:
    value: Any = None
    state: str = "not_specified"
    evidence: str | None = None
    source: str | None = None

    @classmethod
    def coerce(cls, x) -> "Field":
        if isinstance(x, Field):
            return x
        if isinstance(x, dict) and "state" in x:
            return cls(x.get("value"), x.get("state"), x.get("evidence"), x.get("source"))
        return cls(x, "provided" if x is not None else "not_specified")


@dataclass
class OrderSpec:
    """Built from the enquiry alone. Every attribute is a Field."""
    fields: dict[str, Field] = field(default_factory=dict)
    raw_text: str = ""

    def get(self, k: str) -> Field:
        return self.fields.get(k, Field())

    def val(self, k: str):
        return self.get(k).value

    def provided(self, k: str) -> bool:
        return self.get(k).state == "provided"

    @classmethod
    def from_dict(cls, d: dict) -> "OrderSpec":
        o = cls(raw_text=d.get("raw_text", "") or d.get("input", ""))
        for k, v in d.items():
            if k in ("raw_text", "input", "source_type", "source", "_id",
                     "_fingerprint", "_source"):
                continue
            o.fields[k] = Field.coerce(v)
        return o

    def to_dict(self) -> dict:
        out = {k: asdict(v) for k, v in self.fields.items()}
        out["raw_text"] = self.raw_text
        return out


@dataclass
class BuildSpec:
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, k, default=None):
        return self.data.get(k, default)

    def set(self, k, v):
        self.data[k] = v

    @classmethod
    def from_dict(cls, d: dict) -> "BuildSpec":
        d = d.get("build_spec", d) if isinstance(d, dict) else {}
        return cls({k: v for k, v in d.items() if not k.startswith("_")})

    def to_dict(self) -> dict:
        return dict(self.data)


@dataclass
class ClarificationItem:
    code: str
    field: str
    question: str
    why: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class ClarificationList:
    blocking: list[ClarificationItem] = field(default_factory=list)
    advisory: list[ClarificationItem] = field(default_factory=list)
    assumptions_made: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "blocking": [asdict(x) for x in self.blocking],
            "advisory": [asdict(x) for x in self.advisory],
            "assumptions_made": self.assumptions_made,
            "n_questions": len(self.blocking) + len(self.advisory),
        }


@dataclass
class PipelineResult:
    order_spec: dict
    build_spec: dict
    physical_bom: dict
    clarification: dict
    validation: dict
    meta: dict = field(default_factory=dict)
