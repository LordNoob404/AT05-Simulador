"""Validacao de amostras e de configuracao (RF09 / RNF05) — AT05 Equipe 3.

Funcoes puras (sem estado): presença, tipo numerico, faixas fisicas dos canais,
timeout de aquisicao e limites eletricos medidos. O Supervisor (supervisor.py)
consome este modulo e adiciona apenas a parte com estado (historico de timestamp,
contador de travamento, latch de causa e histerese de rearme).
"""
import math

T_MIN_CANAL, T_MAX_CANAL = -20.0, 100.0
V_MIN_CANAL, V_MAX_CANAL = 0.0, 500.0
I_MIN_CANAL, I_MAX_CANAL = -200.0, 200.0
TIMEOUT_S = 1.0


def is_valid_number(val) -> bool:
    """Presenca + tipo numerico finito (rejeita None, NaN e inf)."""
    return (val is not None and isinstance(val, (int, float))
            and not math.isnan(val) and not math.isinf(val))


def check_ranges(T: float, V: float, I: float) -> tuple[bool, str]:
    """Faixas fisicas dos canais virtuais (AT04 §3)."""
    if not (T_MIN_CANAL <= T <= T_MAX_CANAL):
        return False, "T_FORA_DE_FAIXA_SENSOR"
    if not (V_MIN_CANAL <= V <= V_MAX_CANAL):
        return False, "V_FORA_DE_FAIXA_SENSOR"
    if not (I_MIN_CANAL <= I <= I_MAX_CANAL):
        return False, "I_FORA_DE_FAIXA_SENSOR"
    return True, "OK"


def check_timeout(timestamp: float, last_timestamp: float | None) -> tuple[bool, str]:
    """Integridade temporal: amostra nova, monotônica e com idade <= 1 s (RNF01/RF09)."""
    if last_timestamp is None:
        return True, "OK"
    dt_sample = float(timestamp) - last_timestamp
    if dt_sample <= 0.0 or dt_sample > TIMEOUT_S + 1e-9:
        return False, "AMOSTRA_VENCIDA_TIMEOUT"
    return True, "OK"


def check_measured_electrical_limits(V: float, I: float, Vmax: float, Imax: float,
                                     Pmax: float) -> tuple[bool, str]:
    """Limites eletricos sobre valores medidos (C6): V, I e P=V*I."""
    if V > Vmax + 1e-6:
        return False, "SOBRETENSAO_MEDIDA"
    if I > Imax + 1e-6 or I < -1e-6:
        return False, "SOBRECORRENTE_MEDIDA"
    if V * I > Pmax + 1e-3:
        return False, "SOBREPOTENCIA_MEDIDA"
    return True, "OK"


def validate_sample_stateless(timestamp, T_med, V_med, I_med,
                              Vmax: float, Imax: float, Pmax: float,
                              last_timestamp=None) -> tuple[bool, str]:
    """Pipeline RF09 sem estado: presença -> timeout -> faixa -> limites medidos."""
    if not (is_valid_number(timestamp) and is_valid_number(T_med)
            and is_valid_number(V_med) and is_valid_number(I_med)):
        return False, "AMOSTRA_AUSENTE_OU_NAO_NUMERICA"
    ok, reason = check_timeout(float(timestamp), last_timestamp)
    if not ok:
        return False, reason
    T, V, I = float(T_med), float(V_med), float(I_med)
    ok, reason = check_ranges(T, V, I)
    if not ok:
        return False, reason
    return check_measured_electrical_limits(V, I, Vmax, Imax, Pmax)


def validate_config(cfg) -> tuple[bool, str]:
    """RNF05: domínio de parâmetros (delega a model.validate_model_domain)."""
    from model import validate_model_domain
    return validate_model_domain(cfg)
