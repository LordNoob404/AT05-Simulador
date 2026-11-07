from model import ModelConfig
from supervisor import Sample, Supervisor


def test_06_injecao_falhas_c6_mesmo_ciclo():
    cfg = ModelConfig(Iperfil=150.0)
    fault_samples = [
        Sample(timestamp=1.0, T_med=25.0, V_med=405.0, I_med=100.0, z_est=0.5),
        Sample(timestamp=1.0, T_med=25.0, V_med=325.0, I_med=155.0, z_est=0.5),
        Sample(timestamp=1.0, T_med=25.0, V_med=402.0, I_med=150.0, z_est=0.5),
        Sample(timestamp=1.0, T_med=float("nan"), V_med=325.0, I_med=100.0, z_est=0.5),
        Sample(timestamp=1.0, T_med=None, V_med=325.0, I_med=100.0, z_est=0.5),
        Sample(timestamp=2.5, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.5),
        Sample(timestamp=1.0, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.5, stuck_fault=True),
    ]
    for s in fault_samples:
        sup = Supervisor(cfg)
        sup.evaluate(Sample(timestamp=0.0, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.5))
        out = sup.evaluate(s, check_timeout=True)
        assert out.state == "FALHA" and out.Icmd == 0.0 and out.alarm_code != "NONE"


def test_07_configuracao_c7_e_rnf03():
    sup = Supervisor(ModelConfig())
    ok1, _ = sup.update_config(ModelConfig(Td=42.0, Tc=58.0))
    assert ok1 and sup.cfg.Td == 42.0
    ok2, _ = sup.update_config(ModelConfig(Td=60.0, Tc=55.0))
    assert not ok2 and sup.cfg.Td == 42.0

