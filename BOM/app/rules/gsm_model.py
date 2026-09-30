from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[3]


FEATURES = [
    "swl_kg",
    "sf",
    "ext_length",
    "ext_width",
    "ext_height",
    "int_length",
    "int_width",
    "int_height",
    "has_printing",
    "has_liner",
    "has_ds_spout",
    "has_fs_spout",
    "has_ddp",
    "has_doc",
    "loop_width_mm",
    "design_load_kg",
]


@lru_cache(maxsize=1)
def _u_panel_body_gsm_model() -> Pipeline | None:
    path = PROJECT_ROOT / "u_pannel_model_data_CORRECTED.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df = df[df["body_gsm"].notna()]
    df = df[pd.to_numeric(df["body_gsm"], errors="coerce").notna()]
    if len(df) < 12:
        return None
    for col in FEATURES + ["body_gsm"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    x = df[FEATURES]
    y = df["body_gsm"].astype(float)
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestRegressor(n_estimators=80, random_state=42, min_samples_leaf=2)),
    ])
    model.fit(x, y)
    return model


def predict_u_panel_body_gsm(
    swl_kg: float,
    sf: float,
    ext_L: float,
    ext_W: float,
    ext_H: float,
    int_L: float,
    int_W: float,
    int_H: float,
    has_printing: bool,
    has_liner: bool,
    has_ds_spout: bool,
    has_fs_spout: bool,
    has_ddp: bool,
    has_doc: bool,
    loop_width_mm: float | None,
    allowed_values: list[float],
    minimum: int,
) -> int | None:
    model = _u_panel_body_gsm_model()
    if model is None:
        return None
    row = pd.DataFrame([{
        "swl_kg": swl_kg,
        "sf": sf,
        "ext_length": ext_L,
        "ext_width": ext_W,
        "ext_height": ext_H,
        "int_length": int_L,
        "int_width": int_W,
        "int_height": int_H,
        "has_printing": int(has_printing),
        "has_liner": int(has_liner),
        "has_ds_spout": int(has_ds_spout),
        "has_fs_spout": int(has_fs_spout),
        "has_ddp": int(has_ddp),
        "has_doc": int(has_doc),
        "loop_width_mm": loop_width_mm,
        "design_load_kg": swl_kg * sf,
    }])
    prediction = float(model.predict(row[FEATURES])[0])
    legal = sorted(float(v) for v in allowed_values if float(v) >= minimum)
    if not legal:
        return minimum
    nearest = min(legal, key=lambda v: abs(v - prediction))
    return int(np.ceil(nearest))
