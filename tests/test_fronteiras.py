from model import ModelConfig
from supervisor import Sample, Supervisor
from scenarios import C5_GUIDE_POINTS, C5_TRUE_TRANSITION_POINTS


def test_05_fronteiras_c5_e_histerese_rearme():
    cfg = ModelConfig(Iperfil=150.0)
    for t_med, expected_state in C5_GUIDE_POINTS + C5_TRUE_TRANSITION_POINTS:
        sup = Supervisor(cfg)
        out = sup.evaluate(Sample(timestamp=0.0, T_med=t_med, V_med=325.0, I_med=100.0, z_est=0.5))
        assert out.state == expected_state

    # Verifica que o código de alarme de temperatura alta permanece retido mesmo após resfriar abaixo de Tc
    sup_blk = Supervisor(cfg)
    out1 = sup_blk.evaluate(Sample(timestamp=0.0, T_med=60.0, V_med=325.0, I_med=0.0, z_est=0.5))
    out2 = sup_blk.evaluate(Sample(timestamp=1.0, T_med=58.0, V_med=325.0, I_med=0.0, z_est=0.5))
    assert out1.alarm_code == "TEMP_ALTA_CRITICA" and out2.alarm_code == "TEMP_ALTA_CRITICA"

    # Rearme manual com histerese de 2 °C (Tsup <= 43 °C e Tinf >= 12 °C)
    ok_fail, _ = sup_blk.manual_reset(Sample(timestamp=2.0, T_med=43.0, V_med=325.0, I_med=0.0, z_est=0.5))
    assert not ok_fail
    ok_pass, _ = sup_blk.manual_reset(Sample(timestamp=3.0, T_med=42.5, V_med=325.0, I_med=0.0, z_est=0.5))
    assert ok_pass and sup_blk.state == "CARGA_NORMAL"

