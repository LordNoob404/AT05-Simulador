"""Testes do modulo validate.py (RF09/RNF05): bordas de faixa, timeout, limites e config."""
import math
import pytest
from model import ModelConfig
from supervisor import Sample, Supervisor
import validate as VA


def test_numeros_invalidos():
    assert not VA.is_valid_number(None)
    assert not VA.is_valid_number(float("nan"))
    assert not VA.is_valid_number(float("inf"))
    assert not VA.is_valid_number("25")
    assert VA.is_valid_number(25.0) and VA.is_valid_number(0)


def test_bordas_de_faixa():
    assert VA.check_ranges(-20.0, 0.0, 0.0) == (True, "OK")
    assert VA.check_ranges(100.0, 500.0, 200.0) == (True, "OK")
    assert VA.check_ranges(100.0, 500.0, -200.0) == (True, "OK")
    assert VA.check_ranges(-20.1, 0.0, 0.0)[1] == "T_FORA_DE_FAIXA_SENSOR"
    assert VA.check_ranges(100.1, 0.0, 0.0)[1] == "T_FORA_DE_FAIXA_SENSOR"
    assert VA.check_ranges(25.0, 500.1, 0.0)[1] == "V_FORA_DE_FAIXA_SENSOR"
    assert VA.check_ranges(25.0, 0.0, 200.1)[1] == "I_FORA_DE_FAIXA_SENSOR"


def test_bordas_de_timeout():
    assert VA.check_timeout(11.0, 10.0) == (True, "OK")      # exatamente 1,0 s: ok
    assert VA.check_timeout(11.0, None) == (True, "OK")      # primeira amostra: ok
    assert VA.check_timeout(10.0, 10.0)[1] == "AMOSTRA_VENCIDA_TIMEOUT"
    assert VA.check_timeout(9.0, 10.0)[1] == "AMOSTRA_VENCIDA_TIMEOUT"
    assert VA.check_timeout(11.0 + 2e-9, 10.0)[1] == "AMOSTRA_VENCIDA_TIMEOUT"


def test_bordas_limites_medidos():
    cfg = ModelConfig()
    assert VA.check_measured_electrical_limits(cfg.Vmax, 100.0, cfg.Vmax, cfg.Imax, cfg.Pmax)[0]
    assert VA.check_measured_electrical_limits(cfg.Vmax + 1e-3, 100.0, cfg.Vmax, cfg.Imax, cfg.Pmax)[1] == "SOBRETENSAO_MEDIDA"
    assert VA.check_measured_electrical_limits(325.0, cfg.Imax, cfg.Vmax, cfg.Imax, cfg.Pmax)[0]
    assert VA.check_measured_electrical_limits(402.0, 150.0, cfg.Vmax, cfg.Imax, cfg.Pmax)[1] == "SOBREPOTENCIA_MEDIDA"


def test_supervisor_delega_mesmos_codigos():
    cfg = ModelConfig()
    cases = [
        (dict(timestamp=1.0, T_med=float("nan"), V_med=325.0, I_med=100.0, z_est=0.5), "AMOSTRA_AUSENTE_OU_NAO_NUMERICA"),
        (dict(timestamp=1.0, T_med=-50.0, V_med=325.0, I_med=100.0, z_est=0.5), "T_FORA_DE_FAIXA_SENSOR"),
        (dict(timestamp=1.0, T_med=25.0, V_med=405.0, I_med=100.0, z_est=0.5), "SOBRETENSAO_MEDIDA"),
    ]
    for kw, code in cases:
        sup = Supervisor(cfg)
        out = sup.evaluate(Sample(**kw), check_timeout=False)
        assert out.state == "FALHA" and out.alarm_code == code, (kw, out.alarm_code)


def test_config_incoerente_rejeitada():
    from dataclasses import replace
    ok, _ = VA.validate_config(ModelConfig())
    assert ok
    ok, reason = VA.validate_config(replace(ModelConfig(), Td=60.0, Tc=55.0))
    assert not ok and reason == "LIMITES_TERMICOS_INCOERENTES"
