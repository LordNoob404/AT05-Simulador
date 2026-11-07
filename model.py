"""
Módulo da planta virtual (modelo elétrico, térmico e de SOC) — AT05 Equipe 3.
Natureza: modelo didático virtual concentrado (circuito equivalente resistivo e 1 nó térmico).
Não representa bateria comercial, ensaio físico, calibração ou previsão de vida útil.
"""
from dataclasses import dataclass
import math


@dataclass
class ModelConfig:
    Qn: float = 50.0          # Capacidade nominal [Ah]
    eta: float = 1.0          # Eficiência coulômbica [-]
    R: float = 0.096          # Resistência interna equivalente [Ohm] (96s * 1 mOhm)
    Cth: float = 100000.0     # Capacidade térmica concentrada [J/K]
    H: float = 50.0           # Condutância térmica equivalente [W/K]
    Ta: float = 25.0          # Temperatura ambiente [°C]
    T0: float = 25.0          # Temperatura inicial do pack [°C]
    z0: float = 0.20          # SOC inicial normalizado [-]
    zalvo: float = 0.80       # SOC alvo normalizado [-]
    Iperfil: float = 25.0     # Corrente do perfil de carga [A]
    Tmin: float = 10.0        # Limite mínimo de temperatura [°C]
    Td: float = 45.0          # Temperatura de início de derating [°C]
    Tc: float = 60.0          # Temperatura crítica de corte/bloqueio [°C]
    Imax: float = 150.0       # Corrente máxima do carregador [A]
    Vmax: float = 403.2       # Tensão máxima do carregador [V] (96s * 4,2 V)
    Pmax: float = 60000.0     # Potência máxima do carregador [W]
    margem_T: float = 0.5     # Margem de erro da cadeia de temperatura [°C] (RNF07)
    histerese_T: float = 2.0  # Histerese para rearme manual [°C]


@dataclass
class PlantState:
    t: float = 0.0            # Tempo [s]
    z: float = 0.20           # SOC normalizado [-] (0 a 1)
    T: float = 25.0           # Temperatura do nó térmico [°C]
    V: float = 311.04         # Tensão terminal [V]
    I: float = 0.0            # Corrente aplicada [A]
    P: float = 0.0            # Potência elétrica nos terminais [W]
    E_J: float = 0.0          # Energia elétrica acumulada [J]
    Er_J: float = 0.0         # Perda resistiva (Joule) acumulada [J]


def validate_model_domain(cfg: ModelConfig) -> tuple[bool, str]:
    """Valida parâmetros físicos e de configuração conforme hipóteses H1–H10."""
    if cfg.Qn <= 0 or cfg.R <= 0 or cfg.Cth <= 0 or cfg.H <= 0:
        return False, "PARAM_FISICO_NAO_POSITIVO"
    if not (0.0 < cfg.eta <= 1.0):
        return False, "ETA_FORA_DOMINIO"
    if not (cfg.Tmin < cfg.Td < cfg.Tc):
        return False, "LIMITES_TERMICOS_INCOERENTES"
    if cfg.Imax <= 0 or cfg.Vmax <= 0 or cfg.Pmax <= 0:
        return False, "LIMITES_ELETRICOS_NAO_POSITIVOS"
    if cfg.Iperfil < 0 or cfg.Iperfil > cfg.Imax:
        return False, "IPERFIL_FORA_DOMINIO"
    if not (0.0 <= cfg.z0 <= 1.0) or not (0.0 < cfg.zalvo <= 1.0) or cfg.z0 >= cfg.zalvo:
        return False, "SOC_CONFIG_INVALIDA"
    if not (-20.0 <= cfg.T0 <= 100.0) or not (-20.0 <= cfg.Ta <= 100.0):
        return False, "TEMP_INICIAL_FORA_DOMINIO"
    return True, "OK"


def uoc(z: float) -> float:
    """Eq. (1): Tensão de circuito aberto Uoc(z) = 288 + 115,2*z [V], z em [0, 1]."""
    z_clip = min(1.0, max(0.0, float(z)))
    return 288.0 + 115.2 * z_clip


def electrical(z: float, current: float, R: float = 0.096) -> tuple[float, float]:
    """Eq. (2) e (3): Tensão terminal V = Uoc(z) + R*I [V] e potência P = V*I [W]."""
    i_pos = max(0.0, float(current))
    v = uoc(z) + R * i_pos
    p = v * i_pos
    return v, p


def joule_heating(current: float, R: float = 0.096) -> float:
    """Parcela resistiva de geração de calor I^2 * R [W] (H5: P = V*I não aquece o nó)."""
    return (max(0.0, float(current)) ** 2) * R


def thermal_equilibrium(current: float, Ta: float, H: float, R: float = 0.096) -> float:
    """Eq. (12): Temperatura de equilíbrio teórico T_inf = Ta + I^2 * R / H [°C]."""
    if H <= 0:
        raise ValueError("Condutância térmica H deve ser positiva.")
    return Ta + joule_heating(current, R) / H


def thermal_time_constant(Cth: float = 100000.0, H: float = 50.0) -> float:
    """Eq. (13): Constante de tempo térmica tau = Cth / H [s]."""
    if H <= 0:
        raise ValueError("Condutância térmica H deve ser positiva.")
    return Cth / H


def analytical_temperature(t: float, T0: float, current: float, Ta: float, H: float,
                           Cth: float = 100000.0, R: float = 0.096) -> float:
    """Eq. (11): Solução analítica T(t) = T_inf + (T0 - T_inf)*exp(-t/tau) para I, Ta, H constantes."""
    t_inf = thermal_equilibrium(current, Ta, H, R)
    tau = thermal_time_constant(Cth, H)
    return t_inf + (T0 - t_inf) * math.exp(-t / tau)


def ideal_charge_time_s(I: float, Qn: float = 50.0, z0: float = 0.20, zalvo: float = 0.80, eta: float = 1.0) -> float:
    """Eq. (7): Tempo ideal de carga t_ideal = 3600 * Qn * (zalvo - z0) / (eta * I) [s]."""
    if I <= 0:
        raise ValueError("Corrente deve ser estritamente positiva.")
    delta_q = Qn * (zalvo - z0)
    return 3600.0 * delta_q / (eta * I)


def derivatives(z: float, T: float, current: float, cfg: ModelConfig, H_override: float | None = None) -> tuple[float, float]:
    """Eq. (5) e (10): Derivadas dz/dt [1/s] e dT/dt [°C/s]."""
    H_val = cfg.H if H_override is None else H_override
    i_val = min(cfg.Imax, max(0.0, float(current)))
    dz = (cfg.eta * i_val) / (3600.0 * cfg.Qn)
    dT = (joule_heating(i_val, cfg.R) - H_val * (T - cfg.Ta)) / cfg.Cth
    return dz, dT


def step(state: PlantState, current: float, dt: float, cfg: ModelConfig, H_override: float | None = None) -> PlantState:
    """
    Eq. (4), (8) e (14): Avança um passo de integração Euler explícito na planta.
    Não satura T silenciosamente para permitir que o supervisor detecte excursões fora de [-20, 100] °C.
    """
    i_cmd = min(cfg.Imax, max(0.0, float(current)))
    v_now, p_now = electrical(state.z, i_cmd, cfg.R)
    q_joule = joule_heating(i_cmd, cfg.R)

    dz, dT = derivatives(state.z, state.T, i_cmd, cfg, H_override=H_override)

    next_z = min(1.0, max(0.0, state.z + dz * dt))
    next_T = state.T + dT * dt  # Eq. (14) pura; supervisor valida faixa [-20, 100] °C
    next_E_J = state.E_J + p_now * dt
    next_Er_J = state.Er_J + q_joule * dt
    next_t = round(state.t + dt, 6)
    next_V, next_P = electrical(next_z, i_cmd, cfg.R)

    return PlantState(
        t=next_t,
        z=next_z,
        T=next_T,
        V=next_V,
        I=i_cmd,
        P=next_P,
        E_J=next_E_J,
        Er_J=next_Er_J,
    )

