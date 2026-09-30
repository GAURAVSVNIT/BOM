"""Config loader must produce real nested dataclasses (not dicts) or train.py
blows up at `cfg.model.name` on the cluster."""
from pathlib import Path

import pytest

from bomft.config import load_config, to_dict, ModelCfg, LoraCfg, TrainCfg

CFG = Path(__file__).parents[1] / "configs"


@pytest.mark.parametrize("name", ["adapter_a.yaml", "adapter_b.yaml", "serve.yaml"])
def test_nested_sections_are_dataclasses(name):
    c = load_config(CFG / name)
    assert isinstance(c.model, ModelCfg)
    assert isinstance(c.lora, LoraCfg)
    assert isinstance(c.train, TrainCfg)
    assert isinstance(c.model.name, str)
    assert isinstance(c.model.enable_thinking, bool)


def test_dotted_overrides_coerce_types():
    c = load_config(CFG / "adapter_b.yaml",
                    ["train.epochs=5", "model.load_in_4bit=true",
                     "model.enable_thinking=true", "lora.r=8"])
    assert c.train.epochs == 5.0
    assert c.model.load_in_4bit is True
    assert c.model.enable_thinking is True
    assert c.lora.r == 8


def test_unknown_key_rejected(tmp_path):
    load_config(CFG / "adapter_a.yaml")                 # baseline parses fine
    bad = tmp_path / "bad.yaml"
    bad.write_text("model:\n  nonsense: 1\n")
    with pytest.raises(KeyError):
        load_config(bad)


def test_to_dict_roundtrips():
    c = load_config(CFG / "adapter_a.yaml")
    d = to_dict(c)
    assert d["model"]["name"] == c.model.name
    assert set(d) >= {"model", "lora", "train", "data"}
