import math
from model import (
    ModelConfig, PlantState, uoc, electrical, joule_heating,
    thermal_equilibrium, ideal_charge_time_s, step
)
from supervisor import compute_electrical_limits


def test_01_repouso_corrente_zero():
    cfg = ModelConfig(Ta=25.0, T0=40.0)
    v, p = electrical(0.20, 0.0, cfg.R)
    assert math.isclose(v, uoc(0.20), abs_tol=1e-9)
    assert math.isclose(p, 0.0, abs_tol=1e-9)
    st = PlantState(t=0.0, z=0.20, T=40.0, V=v, I=0.0, P=0.0)
    st_next = step(st, 0.0, 1.0, cfg)
    assert 25.0 < st_next.T < 40.0


def test_02_conferencias_eletricas_e_limitadores():
    v25, p25 = electrical(0.20, 25.0, 0.096)
    v150, p150 = electrical(0.20, 150.0, 0.096)
    assert math.isclose(uoc(0.20), 311.04, abs_tol=1e-2)
    assert math.isclose(uoc(0.80), 380.16, abs_tol=1e-2)
    assert math.isclose(v25, 313.44, abs_tol=1e-2) and math.isclose(p25, 7836.0, abs_tol=1e-2)
    assert math.isclose(v150, 325.44, abs_tol=1e-2) and math.isclose(p150, 48816.0, abs_tol=1e-2)

    cfg = ModelConfig(Iperfil=150.0)
    ilim_20, ip_20, iv_20 = compute_electrical_limits(0.20, cfg)
    ilim_80, ip_80, iv_80 = compute_electrical_limits(0.80, cfg)
    assert math.isclose(ip_20, 182.6, abs_tol=0.1) and math.isclose(iv_20, 960.0, abs_tol=0.1)
    assert math.isclose(ip_80, 152.0, abs_tol=0.1) and math.isclose(iv_80, 240.0, abs_tol=0.1)
    assert ilim_20 == 150.0 and ilim_80 == 150.0


def test_03_joule_e_equilibrio_termico():
    assert math.isclose(joule_heating(25.0, 0.096), 60.0, abs_tol=1e-3)
    assert math.isclose(joule_heating(150.0, 0.096), 2160.0, abs_tol=1e-3)
    assert math.isclose(thermal_equilibrium(25.0, 25.0, 50.0), 26.2, abs_tol=0.05)
    assert math.isclose(thermal_equilibrium(150.0, 25.0, 50.0), 68.2, abs_tol=0.05)
    assert math.isclose(thermal_equilibrium(150.0, 40.0, 25.0), 126.4, abs_tol=0.05)


def test_04_tempos_ideais_carga():
    t25 = ideal_charge_time_s(25.0)
    t150 = ideal_charge_time_s(150.0)
    assert math.isclose(t25, 4320.0, abs_tol=1.0) and t25 != 1200.0
    assert math.isclose(t150, 720.0, abs_tol=1.0) and t150 != 200.0

