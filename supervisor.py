"""
Módulo do Supervisor Amostrado (BMS Conceitual) — AT05 Equipe 3.
Implementa validação de presença/faixa/timeout/coerência, margens, derating, limitadores e 6 estados.
"""
from dataclasses import dataclass
import math
from model import ModelConfig, uoc, validate_model_domain
from validate import (
    is_valid_number as _is_valid_number,
    validate_config,
    validate_sample_stateless,
)


@dataclass
class Sample:
    timestamp: float | None
    T_med: float | None
    V_med: float | None
    I_med: float | None
    z_est: float
    stuck_fault: bool = False


@dataclass
class SupervisorOutput:
    state: str
    Icmd: float
    Ilim: float
    IP: float
    IV: float
    alpha: float
    Tsup: float
    Tinf: float
    valid: bool
    alarm_code: str


def compute_margins(T_med: float, margem_T: float = 0.5) -> tuple[float, float]:
    """Eq. (15) e (16): Tsup = Tmed + 0,5 °C (aquecimento) e Tinf = Tmed - 0,5 °C (frio)."""
    return T_med + margem_T, T_med - margem_T


def compute_alpha(Tsup: float, Td: float = 45.0, Tc: float = 60.0) -> float:
    """Eq. (17): Fator de derating linear entre Td e Tc."""
    if Tsup <= Td:
        return 1.0
    if Tsup >= Tc:
        return 0.0
    return (Tc - Tsup) / (Tc - Td)


def compute_electrical_limits(z: float, cfg: ModelConfig) -> tuple[float, float, float]:
    """Eq. (18), (19) e (20): Calcula IV, IP e Ilim = min(Iperfil, Imax, IP, IV) [A]."""
    u = uoc(z)
    iv = max(0.0, (cfg.Vmax - u) / cfg.R)
    ip = (math.sqrt(u * u + 4.0 * cfg.R * cfg.Pmax) - u) / (2.0 * cfg.R)
    ilim = min(cfg.Iperfil, cfg.Imax, ip, iv)
    return ilim, ip, iv


class Supervisor:
    """Supervisor amostrado a 1 s com retenção de causa primária de falha e bloqueio."""

    def __init__(self, cfg: ModelConfig, check_model_coherence: bool = False):
        ok, reason = validate_model_domain(cfg)
        if not ok:
            raise ValueError(f"Configuração inicial inválida: {reason}")
        self.cfg = cfg
        self.check_model_coherence = check_model_coherence
        self.state = "INICIALIZACAO"
        self.last_timestamp: float | None = None
        self.last_T_med: float | None = None
        self.repeated_T_count: int = 0
        self.latched_fault_reason: str | None = None
        self.latched_thermal_block: bool = False
        self.latched_thermal_reason: str | None = None

    def update_config(self, new_cfg: ModelConfig) -> tuple[bool, str]:
        """RNF05: Valida e aplica novos limites sem editar código; mantém anterior se incoerente."""
        ok, reason = validate_config(new_cfg)
        if not ok:
            return False, reason
        self.cfg = new_cfg
        return True, "CONFIG_APLICADA"

    def manual_reset(self, sample: Sample) -> tuple[bool, str]:
        """
        Rearme manual de BLOQUEIO ou FALHA:
        Exige amostra válida e histerese térmica: Tsup <= Td - 2 °C e Tinf >= Tmin + 2 °C.
        """
        valid, reason = self.validate_sample(sample, check_timeout=False)
        if not valid:
            return False, f"REARME_NEGADO_{reason}"
        Tsup, Tinf = compute_margins(float(sample.T_med), self.cfg.margem_T)
        if Tsup <= (self.cfg.Td - self.cfg.histerese_T) and Tinf >= (self.cfg.Tmin + self.cfg.histerese_T):
            self.latched_thermal_block = False
            self.latched_thermal_reason = None
            self.latched_fault_reason = None
            self.repeated_T_count = 0
            self.state = "CARGA_NORMAL"
            return True, "REARME_OK"
        return False, "REARME_NEGADO_HISTERESE"

    def validate_sample(self, sample: Sample, check_timeout: bool = True) -> tuple[bool, str]:
        """RF09: Presença -> numérico -> faixa -> timestamp (<= 1 s) -> coerência e limites.

        Parte sem estado delegada a validate.py; aqui só o contador de travamento
        (com estado) e a coerência opcional com o modelo.
        """
        valid, reason = validate_sample_stateless(
            sample.timestamp, sample.T_med, sample.V_med, sample.I_med,
            self.cfg.Vmax, self.cfg.Imax, self.cfg.Pmax,
            last_timestamp=self.last_timestamp if check_timeout else None,
        )
        if not valid:
            return False, reason

        T = float(sample.T_med)
        V = float(sample.V_med)
        I = float(sample.I_med)

        # Detecção de travamento com inconsistência física (constante por >= 5 ciclos sob alta geração térmica)
        if sample.stuck_fault:
            return False, "TRAVAMENTO_SENSOR_INCONSISTENTE"
        if self.last_T_med is not None and abs(T - self.last_T_med) < 1e-12:
            dT_expected = abs((I ** 2) * self.cfg.R - self.cfg.H * (T - self.cfg.Ta)) / self.cfg.Cth
            if dT_expected > 0.005:  # Mudança esperada relevante
                self.repeated_T_count += 1
                if self.repeated_T_count >= 5:
                    return False, "TRAVAMENTO_SENSOR_INCONSISTENTE"
        else:
            self.repeated_T_count = 0

        if self.check_model_coherence:
            v_expected = uoc(sample.z_est) + self.cfg.R * I
            if abs(V - v_expected) > 15.0:
                return False, "INCOERENCIA_MODELO_TENSAO"

        return True, "OK"

    def evaluate(self, sample: Sample, supervision_enabled: bool = True,
                 check_timeout: bool = True) -> SupervisorOutput:
        """
        Avalia amostra e define estado e Icmd [A] (Eq. 21).
        Retém a primeira causa de FALHA ou BLOQUEIO até rearme manual.
        """
        ilim, ip, iv = compute_electrical_limits(sample.z_est, self.cfg)
        valid, reason = self.validate_sample(sample, check_timeout=check_timeout)

        if _is_valid_number(sample.timestamp):
            self.last_timestamp = float(sample.timestamp)
        if _is_valid_number(sample.T_med):
            self.last_T_med = float(sample.T_med)

        if not valid:
            self.state = "FALHA"
            if self.latched_fault_reason is None:
                self.latched_fault_reason = reason
            t_med_safe = float(sample.T_med) if _is_valid_number(sample.T_med) else math.nan
            tsup, tinf = (compute_margins(t_med_safe, self.cfg.margem_T)
                          if not math.isnan(t_med_safe) else (math.nan, math.nan))
            return SupervisorOutput(
                state="FALHA", Icmd=0.0, Ilim=ilim, IP=ip, IV=iv,
                alpha=0.0, Tsup=tsup, Tinf=tinf, valid=False, alarm_code=self.latched_fault_reason
            )

        Tsup, Tinf = compute_margins(float(sample.T_med), self.cfg.margem_T)

        if self.latched_fault_reason is not None:
            self.state = "FALHA"
            return SupervisorOutput(
                state="FALHA", Icmd=0.0, Ilim=ilim, IP=ip, IV=iv,
                alpha=0.0, Tsup=Tsup, Tinf=Tinf, valid=True, alarm_code=self.latched_fault_reason
            )

        # Bloqueio por temperatura crítica (Tsup >= Tc) ou subtemperatura (Tinf < Tmin estrito)
        if Tsup >= self.cfg.Tc or Tinf < self.cfg.Tmin or self.latched_thermal_block:
            self.state = "BLOQUEIO"
            if not self.latched_thermal_block:
                self.latched_thermal_block = True
                self.latched_thermal_reason = (
                    "TEMP_ALTA_CRITICA" if Tsup >= self.cfg.Tc else "TEMP_BAIXA_BLOQUEIO"
                )
            return SupervisorOutput(
                state="BLOQUEIO", Icmd=0.0, Ilim=ilim, IP=ip, IV=iv,
                alpha=0.0, Tsup=Tsup, Tinf=Tinf, valid=True, alarm_code=self.latched_thermal_reason
            )

        if sample.z_est >= self.cfg.zalvo - 1e-9:
            self.state = "CONCLUIDO"
            return SupervisorOutput(
                state="CONCLUIDO", Icmd=0.0, Ilim=ilim, IP=ip, IV=iv,
                alpha=1.0, Tsup=Tsup, Tinf=Tinf, valid=True, alarm_code="NONE"
            )

        if supervision_enabled and Tsup > self.cfg.Td:
            alpha = compute_alpha(Tsup, self.cfg.Td, self.cfg.Tc)
            self.state = "DERATING"
            return SupervisorOutput(
                state="DERATING", Icmd=alpha * ilim, Ilim=ilim, IP=ip, IV=iv,
                alpha=alpha, Tsup=Tsup, Tinf=Tinf, valid=True, alarm_code="DERATING_TERMICO"
            )

        self.state = "CARGA_NORMAL"
        return SupervisorOutput(
            state="CARGA_NORMAL", Icmd=ilim, Ilim=ilim, IP=ip, IV=iv,
            alpha=1.0, Tsup=Tsup, Tinf=Tinf, valid=True, alarm_code="NONE"
        )

