import math
import os
import tempfile
from scenarios import get_scenarios
from run_simulation import run_scenario, save_artifacts


def test_08_convergencia_numerica_sem_arredondamento_precoce():
    sc_c4 = get_scenarios()["C4"]
    _, m_01 = run_scenario(sc_c4, dt=0.1, supervisor_period_s=1.0)
    _, m_005 = run_scenario(sc_c4, dt=0.05, supervisor_period_s=1.0)
    diff_tmax_pct = 100.0 * abs(m_01["Tmax_raw_C"] - m_005["Tmax_raw_C"]) / m_005["Tmax_raw_C"]
    diff_time_pct = 100.0 * abs(m_01["tempo_carga_raw_s"] - m_005["tempo_carga_raw_s"]) / m_005["tempo_carga_raw_s"]
    assert diff_tmax_pct <= 1.0 and diff_time_pct <= 1.0


def test_09_e_10_tabela_secao_9_e_artefatos_c1_a_c7():
    sc = get_scenarios()
    with tempfile.TemporaryDirectory() as tmpdir:
        results = {}
        for sc_id, spec in sc.items():
            rows, metrics = run_scenario(spec, dt=0.1, supervisor_period_s=1.0)
            save_artifacts(sc_id, rows, metrics, out_root=tmpdir)
            results[sc_id] = metrics
            assert os.path.isfile(os.path.join(tmpdir, sc_id, f"{sc_id}.csv"))
            assert os.path.isfile(os.path.join(tmpdir, sc_id, f"{sc_id}_metrics.json"))
            assert os.path.isfile(os.path.join(tmpdir, sc_id, f"{sc_id}_T-P-SOC.png"))

    assert math.isclose(results["C1"]["tempo_carga_min"], 72.00, abs_tol=0.05)
    assert math.isclose(results["C1"]["Tmax_C"], 26.06, abs_tol=0.05)
    assert math.isclose(results["C1"]["energia_kWh"], 10.440, abs_tol=0.005)
    assert math.isclose(results["C2"]["Tmax_C"], 38.06, abs_tol=0.05)
    assert math.isclose(results["C4_sem_protecao"]["Tmax_C"], 57.44, abs_tol=0.10)
    assert math.isclose(results["C4_sem_protecao"]["tempo_acima_Td_min"], 11.57, abs_tol=0.10)
    assert math.isclose(results["C4"]["tempo_carga_min"], 18.03, abs_tol=0.10)
    assert math.isclose(results["C4"]["Tmax_C"], 52.14, abs_tol=0.10)
    assert math.isclose(results["C4"]["tempo_acima_Td_min"], 17.60, abs_tol=0.10)
    assert math.isclose(results["C4"]["energia_kWh"], 10.670, abs_tol=0.010)

