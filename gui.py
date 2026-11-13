"""Interface demonstrativa Tkinter (RNF04/RNF05) — AT05 Equipe 3.

Painel único com curvas T/P/SOC, limites térmicos e elétricos editáveis (validados,
sem editar código) e veredito RNF03. Uso demonstrativo; não homologada e sem medição
de latência real (RNF08 PENDENTE). Execução: ``python gui.py``.
"""
from dataclasses import replace

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except Exception:  # ambiente sem display/Tk: lógica permanece importável/testável
    tk = None
    ttk = None
    messagebox = None
    TK_AVAILABLE = False

from model import ModelConfig
from scenarios import get_scenarios
from run_simulation import run_scenario
from validate import validate_config

LIMIT_FIELDS = (
    ("Td", "Derating Td [°C]"),
    ("Tc", "Corte Tc [°C]"),
    ("Tmin", "Mínimo Tmin [°C]"),
    ("Imax", "Imax [A]"),
    ("Vmax", "Vmax [V]"),
    ("Pmax", "Pmax [W]"),
)
TIME_SCENARIOS = ("C1", "C2", "C3", "C4", "C4_sem_protecao")


def parse_limits(raw: dict, base: ModelConfig) -> tuple:
    """Converte textos da GUI em ModelConfig validado (RNF05). Puro e testável sem display."""
    try:
        vals = {k: float(raw[k]) for k, _ in LIMIT_FIELDS}
    except (KeyError, TypeError, ValueError):
        return None, "LIMITES_NAO_NUMERICOS"
    cfg = replace(base, Td=vals["Td"], Tc=vals["Tc"], Tmin=vals["Tmin"],
                  Imax=vals["Imax"], Vmax=vals["Vmax"], Pmax=vals["Pmax"])
    ok, reason = validate_config(cfg)
    if not ok:
        return None, reason
    return cfg, "CONFIG_APLICADA"


class App:
    """Janela principal: cenário + limites + curvas + métricas + veredito RNF03."""

    def __init__(self, root):
        self.root = root
        root.title("AT05-Simulador — Painel demonstrativo (RNF04/RNF05)")
        self.specs = get_scenarios()
        self.cfg_override = None

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Cenário:").pack(side="left")
        self.sc_var = tk.StringVar(value="C3")
        ttk.Combobox(top, textvariable=self.sc_var, values=list(TIME_SCENARIOS),
                     width=16, state="readonly").pack(side="left", padx=4)
        ttk.Button(top, text="Executar", command=self.on_run).pack(side="left", padx=8)
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(top, textvariable=self.status).pack(side="left", padx=8)

        mid = ttk.Frame(root, padding=8)
        mid.pack(fill="x")
        self.entries = {}
        for i, (key, label) in enumerate(LIMIT_FIELDS):
            ttk.Label(mid, text=label).grid(row=i // 3, column=(i % 3) * 2, sticky="e", padx=2)
            ent = ttk.Entry(mid, width=10)
            ent.grid(row=i // 3, column=(i % 3) * 2 + 1, padx=2)
            self.entries[key] = ent
        self.reset_entries()
        ttk.Button(mid, text="Aplicar limites", command=self.on_apply).pack(pady=4)
        self.cfg_status = tk.StringVar(value="Limites: padrão AT04.")
        ttk.Label(mid, textvariable=self.cfg_status).pack()

        self.fig = None
        self.canvas = None
        self.metrics = tk.StringVar(value="Métricas: —")
        ttk.Label(root, textvariable=self.metrics, justify="left").pack(fill="x", padx=8)
        ttk.Label(root, text="Latência de apresentação (RNF08 ≤ 500 ms): PENDENTE — simulação acelerada não mede tempo real.",
                  foreground="red").pack(fill="x", padx=8, pady=4)

    def reset_entries(self):
        base = ModelConfig()
        for key, _ in LIMIT_FIELDS:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, str(getattr(base, key)))

    def on_apply(self):
        base = ModelConfig()
        raw = {k: e.get() for k, e in self.entries.items()}
        cfg, msg = parse_limits(raw, base)
        if cfg is None:
            self.cfg_status.set(f"Limites rejeitados ({msg}); mantido último válido.")
            return
        self.cfg_override = cfg
        self.cfg_status.set(f"Limites aplicados: Td={cfg.Td} Tc={cfg.Tc} Tmin={cfg.Tmin} "
                            f"Imax={cfg.Imax} Vmax={cfg.Vmax} Pmax={cfg.Pmax}.")

    def on_run(self):
        import matplotlib
        matplotlib.use("TkAgg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        sc_id = self.sc_var.get()
        spec = self.specs[sc_id]
        if self.cfg_override is not None:
            import dataclasses
            spec = dataclasses.replace(spec, cfg=dataclasses.replace(
                spec.cfg, Td=self.cfg_override.Td, Tc=self.cfg_override.Tc,
                Tmin=self.cfg_override.Tmin, Imax=self.cfg_override.Imax,
                Vmax=self.cfg_override.Vmax, Pmax=self.cfg_override.Pmax))
        self.status.set("Executando...")
        self.root.update_idletasks()
        rows, metrics = run_scenario(spec, dt=0.1, supervisor_period_s=1.0)
        t = [r["time_s"] / 60.0 for r in rows]
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.fig, ax = plt.subplots(3, 1, figsize=(7, 6), sharex=True)
        ax[0].plot(t, [r["T_C"] for r in rows]); ax[0].axhline(45, ls="--"); ax[0].axhline(60, ls=":")
        ax[0].set_ylabel("T [°C]")
        ax[1].plot(t, [r["P_W"] / 1000.0 for r in rows]); ax[1].set_ylabel("P [kW]")
        ax[2].plot(t, [r["SOC"] for r in rows]); ax[2].set_ylabel("SOC [%]"); ax[2].set_xlabel("tempo [min]")
        for a in ax:
            a.grid(True, alpha=0.3)
        self.fig.suptitle(f"{sc_id} — {metrics['conclusao']}")
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        verdict = "ATENDE RNF03" if metrics["registros_validos_pct"] >= 99.0 else "REPROVA RNF03"
        self.metrics.set(f"Tmax={metrics['Tmax_C']} °C | t={metrics['tempo_carga_min']} min | "
                         f"E={metrics['energia_kWh']} kWh | válidos={metrics['registros_validos_pct']}% → {verdict}")
        self.status.set("Pronto.")


def main():
    if not TK_AVAILABLE:
        raise SystemExit("Tkinter indisponível neste ambiente.")
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
