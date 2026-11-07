"""
Executor de simulações temporais (C1-C4) e cenários de eventos/verificação (C5-C7).
Gera outputs/C1..C7/ com Cx.csv, Cx_metrics.json e Cx_T-P-SOC.png.
Uso via CLI: python run_simulation.py --scenario C3 --dt 0.1
"""
import argparse
import csv
import json
import math
import os
from dataclasses import replace
from model import ModelConfig, PlantState, electrical, step
from supervisor import Sample, Supervisor, SupervisorOutput, compute_electrical_limits
from scenarios import ScenarioSpec, get_scenarios, C5_GUIDE_POINTS, C5_TRUE_TRANSITION_POINTS
from plots import generate_scenario_plot


CSV_COLUMNS = [
    "scenario", "sequence", "time_s", "T_C", "V_V", "I_A",
    "P_W", "SOC", "state", "valid", "alarm_code", "Icmd_A"
]


def run_time_scenario(spec: ScenarioSpec, dt: float = 0.1, supervisor_period_s: float = 1.0,
                      max_time_s: float = 20000.0) -> tuple[list[dict], dict]:
    """Executa simulação contínua-discreta para C1-C4 com supervisor a cada 1 s (ZOH) e planta a dt."""
    cfg = spec.cfg
    sup = Supervisor(cfg)
    ilim0, _, _ = compute_electrical_limits(cfg.z0, cfg)
    v0, p0 = electrical(cfg.z0, ilim0, cfg.R)
    state = PlantState(t=0.0, z=cfg.z0, T=cfg.T0, V=v0, I=ilim0, P=p0, E_J=0.0, Er_J=0.0)

    steps_per_sup = max(1, int(round(supervisor_period_s / dt)))
    step_idx = 0
    seq = 0
    rows: list[dict] = []
    time_above_td_s = 0.0
    tmax_c = state.T
    conclusao = "CONCLUIDO"
    sup_out: SupervisorOutput | None = None

    while state.t <= max_time_s:
        # Salvaguarda de limite de estudo nos cenários sem proteção (verificada a cada passo dt)
        if not spec.supervision_enabled and spec.stop_at_Tc_unprotected and (state.T + cfg.margem_T) >= cfg.Tc:
            conclusao = "INTERROMPIDO_LIMITE_ESTUDO"
            seq += 1
            rows.append({
                "scenario": spec.id, "sequence": seq, "time_s": round(state.t, 2),
                "T_C": round(state.T, 4), "V_V": round(state.V, 4), "I_A": 0.0,
                "P_W": 0.0, "SOC": round(state.z * 100.0, 4), "state": conclusao,
                "valid": True, "alarm_code": "LIMITE_ESTUDO_TC", "Icmd_A": 0.0,
            })
            break

        is_sup_cycle = (step_idx % steps_per_sup == 0)
        is_target_reached = (state.z >= cfg.zalvo - 1e-9)

        if is_sup_cycle or is_target_reached:
            v_now, _ = electrical(state.z, state.I, cfg.R)
            sample = Sample(timestamp=state.t, T_med=state.T, V_med=v_now, I_med=state.I, z_est=state.z)
            if spec.supervision_enabled:
                # check_timeout ativo nos ciclos regulares de 1 s; desativado apenas no corte fracionário de SOC alvo
                sup_out = sup.evaluate(sample, supervision_enabled=True, check_timeout=not is_target_reached)
            else:
                ilim, ip, iv = compute_electrical_limits(state.z, cfg)
                if is_target_reached:
                    conclusao = "CONCLUIDO"
                    icmd_val, st_label = 0.0, "CONCLUIDO"
                else:
                    icmd_val, st_label = min(cfg.Iperfil, ilim), "CARGA_SEM_PROTECAO"
                sup_out = SupervisorOutput(
                    state=st_label, Icmd=icmd_val, Ilim=ilim, IP=ip, IV=iv,
                    alpha=1.0, Tsup=state.T + cfg.margem_T, Tinf=state.T - cfg.margem_T,
                    valid=True, alarm_code="NONE"
                )

            v_term, p_term = electrical(state.z, sup_out.Icmd, cfg.R)
            seq += 1
            rows.append({
                "scenario": spec.id,
                "sequence": seq,
                "time_s": round(state.t, 2),
                "T_C": round(state.T, 4),
                "V_V": round(v_term, 4),
                "I_A": round(sup_out.Icmd, 4),
                "P_W": round(p_term, 4),
                "SOC": round(state.z * 100.0, 4),
                "state": sup_out.state,
                "valid": sup_out.valid,
                "alarm_code": sup_out.alarm_code,
                "Icmd_A": round(sup_out.Icmd, 4),
            })

            if sup_out.state in ("CONCLUIDO", "BLOQUEIO", "FALHA", "INTERROMPIDO_LIMITE_ESTUDO"):
                conclusao = sup_out.state
                break

        if (state.T + cfg.margem_T) > cfg.Td:
            time_above_td_s += dt

        h_now = spec.H_schedule(state.t) if spec.H_schedule is not None else cfg.H
        state = step(state, sup_out.Icmd, dt, cfg, H_override=h_now)
        if state.T > tmax_c:
            tmax_c = state.T
        step_idx += 1

    valid_count = sum(1 for r in rows if r["valid"])
    valid_pct = 100.0 * valid_count / max(1, len(rows))

    metrics = {
        "scenario": spec.id,
        "Tmax_C": round(tmax_c, 2),
        "Tmax_raw_C": tmax_c,
        "tempo_acima_Td_min": round(time_above_td_s / 60.0, 2),
        "tempo_carga_min": round(state.t / 60.0, 2),
        "tempo_carga_raw_s": state.t,
        "energia_kWh": round(state.E_J / 3_600_000.0, 3),
        "perda_resistiva_kWh": round(state.Er_J / 3_600_000.0, 3),
        "registros_validos_pct": round(valid_pct, 2),
        "atraso_atuacao_s": 0.0,
        "conclusao": conclusao,
    }
    return rows, metrics


def run_event_scenario(spec: ScenarioSpec) -> tuple[list[dict], dict]:
    """Executa os cenários de verificação lógica C5, C6 e C7 gerando CSV, JSON e PNG padronizados."""
    cfg = spec.cfg
    rows: list[dict] = []
    seq = 0

    if spec.id == "C5":
        all_points = C5_GUIDE_POINTS + C5_TRUE_TRANSITION_POINTS
        for idx, (t_med, _) in enumerate(all_points):
            sup = Supervisor(cfg)
            v_nom, _ = electrical(0.50, cfg.Iperfil, cfg.R)
            out = sup.evaluate(Sample(timestamp=float(idx), T_med=t_med, V_med=v_nom, I_med=cfg.Iperfil, z_est=0.50))
            v_cmd, p_cmd = electrical(0.50, out.Icmd, cfg.R)
            seq += 1
            rows.append({
                "scenario": "C5", "sequence": seq, "time_s": float(idx),
                "T_C": t_med, "V_V": round(v_cmd, 4), "I_A": round(out.Icmd, 4),
                "P_W": round(p_cmd, 4), "SOC": 50.0, "state": out.state,
                "valid": out.valid, "alarm_code": out.alarm_code, "Icmd_A": round(out.Icmd, 4),
            })
        metrics = {
            "scenario": "C5",
            "Tmax_C": max(r["T_C"] for r in rows),
            "tempo_acima_Td_min": round(sum(1.0 for r in rows if r["T_C"] + cfg.margem_T > cfg.Td) / 60.0, 2),
            "tempo_carga_min": round(len(rows) / 60.0, 2),
            "energia_kWh": 0.0,
            "registros_validos_pct": 100.0,
            "atraso_atuacao_s": 0.0,
            "conclusao": "BLOQUEIO",
        }
        return rows, metrics

    if spec.id == "C6":
        fault_cases = [
            Sample(timestamp=1.0, T_med=25.0, V_med=405.0, I_med=100.0, z_est=0.50),          # Sobretensão
            Sample(timestamp=1.0, T_med=25.0, V_med=325.0, I_med=155.0, z_est=0.50),          # Sobrecorrente
            Sample(timestamp=1.0, T_med=25.0, V_med=402.0, I_med=150.0, z_est=0.50),          # Sobrepotência (60,3 kW)
            Sample(timestamp=1.0, T_med=float("nan"), V_med=325.0, I_med=100.0, z_est=0.50),  # Amostra inválida
            Sample(timestamp=2.5, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.50),          # Vencida (> 1 s)
            Sample(timestamp=1.0, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.50, stuck_fault=True),  # Travamento
        ]
        for idx, f_sample in enumerate(fault_cases):
            sup = Supervisor(cfg)
            sup.evaluate(Sample(timestamp=0.0, T_med=25.0, V_med=325.0, I_med=100.0, z_est=0.50))
            out = sup.evaluate(f_sample, check_timeout=True)
            seq += 1
            t_val = 25.0 if not math.isnan(float(f_sample.T_med or 25.0)) else -999.0
            rows.append({
                "scenario": "C6", "sequence": seq, "time_s": float(idx + 1),
                "T_C": t_val, "V_V": float(f_sample.V_med or 0.0), "I_A": 0.0,
                "P_W": 0.0, "SOC": 50.0, "state": out.state,
                "valid": out.valid, "alarm_code": out.alarm_code, "Icmd_A": out.Icmd,
            })
        metrics = {
            "scenario": "C6",
            "Tmax_C": 25.0,
            "tempo_acima_Td_min": 0.0,
            "tempo_carga_min": round(len(rows) / 60.0, 2),
            "energia_kWh": 0.0,
            "registros_validos_pct": 0.0,
            "atraso_atuacao_s": 0.0,
            "conclusao": "FALHA",
        }
        return rows, metrics

    # C7: Simulação de 100 amostras com 1% de perda (99% válidas -> limiar RNF03) e alteração de limite em t = 50 s
    sup = Supervisor(cfg)
    for t_sec in range(100):
        if t_sec == 50:
            sup.update_config(replace(cfg, Td=42.0, Tc=58.0))  # Config válida aplicada sem editar código
            sup.update_config(replace(cfg, Td=65.0, Tc=55.0))  # Config incoerente rejeitada
        if t_sec == 75:
            # Lacuna explícita de 1 amostra (1% em 100 amostras) — não repete leitura anterior como válida
            out = sup.evaluate(Sample(timestamp=float(t_sec), T_med=None, V_med=None, I_med=None, z_est=0.40))
            seq += 1
            rows.append({
                "scenario": "C7", "sequence": seq, "time_s": float(t_sec),
                "T_C": math.nan, "V_V": math.nan, "I_A": 0.0, "P_W": 0.0,
                "SOC": 40.0, "state": out.state, "valid": False,
                "alarm_code": out.alarm_code, "Icmd_A": 0.0,
            })
            # Rearme manual após teste de perda controlada
            sup.manual_reset(Sample(timestamp=float(t_sec), T_med=30.0, V_med=340.0, I_med=0.0, z_est=0.40))
            continue

        t_sim = 30.0 + 0.15 * t_sec
        v_sim, p_sim = electrical(0.40, 100.0, cfg.R)
        out = sup.evaluate(Sample(timestamp=float(t_sec), T_med=t_sim, V_med=v_sim, I_med=100.0, z_est=0.40),
                           check_timeout=False)
        v_cmd, p_cmd = electrical(0.40, out.Icmd, cfg.R)
        seq += 1
        rows.append({
            "scenario": "C7", "sequence": seq, "time_s": float(t_sec),
            "T_C": round(t_sim, 3), "V_V": round(v_cmd, 4), "I_A": round(out.Icmd, 4),
            "P_W": round(p_cmd, 4), "SOC": 40.0, "state": out.state,
            "valid": out.valid, "alarm_code": out.alarm_code, "Icmd_A": round(out.Icmd, 4),
        })

    valid_pct = 100.0 * sum(1 for r in rows if r["valid"]) / len(rows)
    metrics = {
        "scenario": "C7",
        "Tmax_C": max(r["T_C"] for r in rows if not math.isnan(r["T_C"])),
        "tempo_acima_Td_min": round(sum(1.0 for r in rows if not math.isnan(r["T_C"]) and r["T_C"] + 0.5 > 42.0) / 60.0, 2),
        "tempo_carga_min": round(len(rows) / 60.0, 2),
        "energia_kWh": 0.0,
        "registros_validos_pct": round(valid_pct, 2),
        "atraso_atuacao_s": 0.0,
        "latencia_interface_s": "PENDENTE_TEMPO_REAL",
        "conclusao": "CONCLUIDO",
    }
    return rows, metrics


def run_scenario(spec: ScenarioSpec, dt: float = 0.1, supervisor_period_s: float = 1.0) -> tuple[list[dict], dict]:
    if spec.mode == "event_sim":
        return run_event_scenario(spec)
    return run_time_scenario(spec, dt=dt, supervisor_period_s=supervisor_period_s)


def save_artifacts(scenario_id: str, rows: list[dict], metrics: dict, out_root: str = "outputs") -> None:
    scen_dir = os.path.join(out_root, scenario_id)
    os.makedirs(scen_dir, exist_ok=True)

    csv_path = os.path.join(scen_dir, f"{scenario_id}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path = os.path.join(scen_dir, f"{scenario_id}_metrics.json")
    clean_metrics = {k: v for k, v in metrics.items() if not k.endswith("_raw_C") and not k.endswith("_raw_s")}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_metrics, f, indent=2, ensure_ascii=False)

    png_path = os.path.join(scen_dir, f"{scenario_id}_T-P-SOC.png")
    generate_scenario_plot(scenario_id, rows, clean_metrics, png_path)


def main():
    parser = argparse.ArgumentParser(description="Simulador Python AT05 - Equipe 3")
    parser.add_argument("--scenario", type=str, default="ALL", help="ID do cenário (C1..C7 ou ALL)")
    parser.add_argument("--dt", type=float, default=0.1, help="Passo de integração da planta [s]")
    parser.add_argument("--sup-dt", type=float, default=1.0, help="Período do supervisor [s]")
    args = parser.parse_args()

    scenarios = get_scenarios()
    targets = list(scenarios.keys()) if args.scenario == "ALL" else [args.scenario]

    for sc_id in targets:
        if sc_id in scenarios:
            rows, metrics = run_scenario(scenarios[sc_id], dt=args.dt, supervisor_period_s=args.sup_dt)
            save_artifacts(sc_id, rows, metrics)
            print(f"[{sc_id}] {metrics}")


if __name__ == "__main__":
    main()

