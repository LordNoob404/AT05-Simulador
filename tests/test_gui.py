"""Testes da lógica da GUI sem display (parse/validação de limites — RNF05)."""
from dataclasses import replace
from model import ModelConfig
import gui


def test_parse_limites_validos():
    raw = {"Td": "45", "Tc": "60", "Tmin": "10", "Imax": "150", "Vmax": "403.2", "Pmax": "60000"}
    cfg, msg = gui.parse_limits(raw, ModelConfig())
    assert cfg is not None and msg == "CONFIG_APLICADA" and cfg.Td == 45.0


def test_parse_limites_rejeitados():
    base = ModelConfig()
    raw_bad_num = {"Td": "abc", "Tc": "60", "Tmin": "10", "Imax": "150", "Vmax": "403.2", "Pmax": "60000"}
    assert gui.parse_limits(raw_bad_num, base)[0] is None
    raw_bad_cfg = {"Td": "60", "Tc": "55", "Tmin": "10", "Imax": "150", "Vmax": "403.2", "Pmax": "60000"}
    cfg, msg = gui.parse_limits(raw_bad_cfg, base)
    assert cfg is None and msg == "LIMITES_TERMICOS_INCOERENTES"


def test_gui_nao_abre_janela_na_importacao():
    assert hasattr(gui, "App") and hasattr(gui, "main")
