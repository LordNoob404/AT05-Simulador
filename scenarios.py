"""
Definições reproduzíveis dos cenários C1 a C7 (Seção 7 do Guia).
Inclui geradores de sequências de teste para C5 (fronteiras/rearme), C6 (falhas) e C7 (configuração/perda).
"""
from dataclasses import dataclass, replace
from typing import Callable
from model import ModelConfig


@dataclass
class ScenarioSpec:
    id: str
    name: str
    cfg: ModelConfig
    mode: str = "time_sim"  # "time_sim" (C1-C4) ou "event_sim" (C5-C7)
    supervision_enabled: bool = True
    stop_at_Tc_unprotected: bool = False
    H_schedule: Callable[[float], float] | None = None
    description: str = ""


def get_scenarios() -> dict[str, ScenarioSpec]:
    base = ModelConfig()
    h_c4 = lambda t: 50.0 if t < 120.0 else 25.0

    return {
        "C1": ScenarioSpec(
            id="C1",
            name="Carga convencional 25 A nominal",
            cfg=replace(base, Iperfil=25.0, Ta=25.0, T0=25.0, H=50.0),
            supervision_enabled=True,
            description="Referência de T, P, energia e tempo (20% a 80% SOC a 25 A).",
        ),
        "C2": ScenarioSpec(
            id="C2",
            name="Carga rápida 150 A sem derating (nominal)",
            cfg=replace(base, Iperfil=150.0, Ta=25.0, T0=25.0, H=50.0),
            supervision_enabled=False,
            stop_at_Tc_unprotected=True,
            description="Efeito acadêmico da corrente alta sem derating térmico (cenário virtual).",
        ),
        "C3": ScenarioSpec(
            id="C3",
            name="Carga rápida 150 A com supervisão (nominal)",
            cfg=replace(base, Iperfil=150.0, Ta=25.0, T0=25.0, H=50.0),
            supervision_enabled=True,
            description="Comparação nominal com C2 sob supervisão completa.",
        ),
        "C4_sem_protecao": ScenarioSpec(
            id="C4_sem_protecao",
            name="C4 crítico sem proteção térmica",
            cfg=replace(base, Iperfil=150.0, Ta=40.0, T0=44.0, H=50.0),
            supervision_enabled=False,
            stop_at_Tc_unprotected=True,
            H_schedule=h_c4,
            description="Ambiente crítico (T0=44 °C, Ta=40 °C, H: 50->25 W/K em 120 s) sem derating.",
        ),
        "C4": ScenarioSpec(
            id="C4",
            name="C4 crítico com supervisão térmica",
            cfg=replace(base, Iperfil=150.0, Ta=40.0, T0=44.0, H=50.0),
            supervision_enabled=True,
            H_schedule=h_c4,
            description="Ambiente crítico (T0=44 °C, Ta=40 °C, H: 50->25 W/K em 120 s) com derating ativo.",
        ),
        "C5": ScenarioSpec(
            id="C5",
            name="Teste de fronteiras térmicas, bloqueio por frio e rearme com histerese",
            cfg=replace(base, Iperfil=150.0),
            mode="event_sim",
            description="Injeção em Td/Tc ±0,1 °C, fronteiras reais com margem ±0,5 °C e rearme manual.",
        ),
        "C6": ScenarioSpec(
            id="C6",
            name="Injeção de falhas elétricas e de aquisição",
            cfg=replace(base, Iperfil=150.0),
            mode="event_sim",
            description="Injeção de V/I/P acima do limite, amostra inválida, vencida (>1 s) e travamento.",
        ),
        "C7": ScenarioSpec(
            id="C7",
            name="Alteração de limites (RNF05) e perda controlada de amostras (RNF03)",
            cfg=replace(base, Iperfil=150.0),
            mode="event_sim",
            description="Edição de limites em runtime, rejeição de incoerência e teste de perda de 1% e 2%.",
        ),
    }


C5_GUIDE_POINTS = [
    (44.9, "DERATING"), (45.0, "DERATING"), (45.1, "DERATING"),
    (59.9, "BLOQUEIO"), (60.0, "BLOQUEIO"), (60.1, "BLOQUEIO"),
    (9.9, "BLOQUEIO"),  (10.0, "BLOQUEIO"), (10.1, "BLOQUEIO"),
]

C5_TRUE_TRANSITION_POINTS = [
    (44.4, "CARGA_NORMAL"), (44.5, "CARGA_NORMAL"), (44.6, "DERATING"),
    (59.4, "DERATING"),     (59.5, "BLOQUEIO"),     (59.6, "BLOQUEIO"),
    (10.4, "BLOQUEIO"),     (10.5, "CARGA_NORMAL"), (10.6, "CARGA_NORMAL"),
]

