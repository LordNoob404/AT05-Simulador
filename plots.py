"""
Módulo de geração de gráficos (T, P, SOC e Icmd versus tempo) com marcação de eventos de falha/bloqueio.
Remove o ponto de parada (CONCLUIDO com Icmd=0) da curva de potência/corrente para evitar queda vertical artificial.
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_scenario_plot(scenario_id: str, rows: list[dict], metrics: dict, out_png: str) -> None:
    plot_rows = rows[:-1] if len(rows) > 2 and rows[-1]["state"] == "CONCLUIDO" else rows

    t_min = [r["time_s"] / 60.0 for r in plot_rows]
    temp = [r["T_C"] if not math.isnan(r["T_C"]) else None for r in plot_rows]
    power_kw = [r["P_W"] / 1000.0 if not math.isnan(r["P_W"]) else None for r in plot_rows]
    soc = [r["SOC"] for r in plot_rows]
    icmd = [r["Icmd_A"] for r in plot_rows]

    fault_t = [r["time_s"] / 60.0 for r in plot_rows if r["state"] in ("FALHA", "BLOQUEIO")]
    fault_icmd = [r["Icmd_A"] for r in plot_rows if r["state"] in ("FALHA", "BLOQUEIO")]

    fig, axes = plt.subplots(4, 1, figsize=(8, 10), sharex=True)
    fig.suptitle(f"Cenário {scenario_id} — Fim: {metrics['conclusao']} (Tmax={metrics['Tmax_C']} °C)")

    axes[0].plot(t_min, temp, color="tab:red", label="T pack [°C]")
    axes[0].axhline(45.0, color="orange", linestyle="--", label="Td = 45 °C")
    axes[0].axhline(60.0, color="darkred", linestyle=":", label="Tc = 60 °C")
    axes[0].set_ylabel("Temperatura [°C]")
    axes[0].legend(loc="best", fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t_min, power_kw, color="tab:purple", label="Potência [kW]")
    axes[1].set_ylabel("Potência [kW]")
    axes[1].legend(loc="best", fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(t_min, soc, color="tab:green", label="SOC [%]")
    axes[2].axhline(80.0, color="gray", linestyle=":", label="Alvo 80%")
    axes[2].set_ylabel("SOC [%]")
    axes[2].legend(loc="best", fontsize=8)
    axes[2].grid(True, alpha=0.3)

    axes[3].step(t_min, icmd, where="post", color="tab:blue", label="Icmd [A]")
    if fault_t:
        axes[3].scatter(fault_t, fault_icmd, color="red", zorder=5, label="Falha/Bloqueio (Icmd=0)")
    axes[3].set_ylabel("Corrente [A]")
    axes[3].set_xlabel("Tempo [min]")
    axes[3].legend(loc="best", fontsize=8)
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close(fig)

