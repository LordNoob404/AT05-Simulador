# AT05-Simulador — Supervisão de Carga de Baterias (Equipe 3 — Certificadora 1)

Simulador Python do sistema **conceitual e virtual** de gerenciamento de carga de baterias de
veículos elétricos (SOC 20 % → 80 %, perfis 25 A / 150 A, supervisor térmico com derating,
limitadores elétricos e 6 estados). Modelo: pack homogêneo, circuito equivalente resistivo,
um nó térmico concentrado — **didático, sem ensaio físico, calibração, certificação (RNF06
pendente) ou previsão de vida útil**. Latência de IHM (RNF08 ≤ 500 ms) **pendente**
(simulação acelerada não comprova tempo real).

## Instalação e execução

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python run_simulation.py --scenario C3 --dt 0.1
python run_simulation.py --scenario ALL --dt 0.1
pytest tests/ -v
```

## Estrutura

`model.py` (planta: equações elétricas/térmicas/SOC) · `supervisor.py` (validação,
margens, derating, limitadores, estados) · `scenarios.py` (C1–C7) ·
`run_simulation.py` (loop planta `dt=0,1 s` + supervisor 1 s com ZOH, CSV/JSON/PNG) ·
`plots.py` (T/P/SOC/Icmd) · `tests/` (aceite) · `outputs/` (artefatos por cenário).

## Resultados de referência (dt = 0,1 s, supervisor 1 s)

| Cenário | Tempo | Tmax | Tempo > Td | Energia | Fim |
|---|---|---|---|---|---|
| C1 25 A | 72,00 min | 26,06 °C | 0,00 min | 10,440 kWh | CONCLUIDO |
| C2 150 A s/ derating | 12,00 min | 38,06 °C | 0,00 min | 10,800 kWh | CONCLUIDO |
| C3 150 A c/ supervisão | 12,00 min | 38,06 °C | 0,00 min | 10,800 kWh | CONCLUIDO |
| C4 s/ proteção | 12,00 min | 57,44 °C | 11,57 min | 10,800 kWh | CONCLUIDO |
| C4 c/ supervisão | 18,03 min | 52,14 °C | 17,60 min | 10,670 kWh | CONCLUIDO |

`tempo_acima_Td` usa **Tsup > Td** em todos os cenários. Decisões de desambiguação
(validação antes dos comparadores, latch de causa primária, parada com tolerância
numérica) documentadas no código e nos testes.
