# AT05-Simulador — Supervisão de Carga de Baterias (Equipe 3 — Certificadora 1)

Simulador Python do sistema **conceitual e virtual** de gerenciamento de carga de baterias de
veículos elétricos: carrega um pack virtual de SOC 20 % → 80 % nos perfis convencional
(25 A ≈ 0,5 C) e rápido (150 A ≈ 3 C), sob supervisão térmica (derating + bloqueio),
limitadores elétricos e máquina de 6 estados.

> **Natureza do modelo (leia antes de usar):** pack homogêneo, circuito equivalente
> **resistivo puro**, **um nó térmico concentrado**. É um modelo **didático de demonstração** —
> não caracteriza bateria comercial, não há ensaio físico, calibração de sensores reais,
> certificação normativa (**RNF06 pendente**) nem previsão de degradação/vida útil.
> A latência de interface (**RNF08 ≤ 500 ms**) está classificada como **PENDENTE**:
> simulação acelerada não comprova tempo real.

Projeto acadêmico encadeado: **AT03** (requisitos RF/RNF) → **AT04** (concepção, parâmetros
didáticos, cenários C1–C7) → **AT05** (este simulador + análise de sensibilidade).

---

## 1. O modelo em 2 minutos

**Planta (integrada por Euler explícito, `dt = 0,1 s`):**

| # | Equação | Significado |
|---|---|---|
| (1) | `Uoc(z) = 288 + 115,2·z` [V] | Tensão de circuito aberto hipotética (`z = SOC/100`) |
| (2) | `V = Uoc(z) + R·I`, `R = 0,096 Ω` | Tensão terminal (sobretensão ôhmica instantânea) |
| (3) | `P = V·I = Uoc·I + R·I²` [W] | Potência elétrica nos terminais — **não** é o calor |
| (5) | `dz/dt = η·I/(3600·Qn)`, `Qn = 50 Ah`, `η = 1` | SOC por contagem de carga (ΔQ = 30 Ah; 4320 s a 25 A, 720 s a 150 A) |
| (9) | `Cth·dT/dt = I²R − H·(T−Ta)`, `Cth = 100 000 J/K`, `H = 50 W/K` | Balanço térmico; **só `I²R` aquece** (60 W a 25 A, 2160 W a 150 A) |

**Supervisor (amostrado a cada 1 s, com retenção de ordem zero entre amostras):**
valida cada amostra (presença → tipo numérico → faixa → timestamp ≤ 1 s → coerência),
aplica margens `Tsup = Tmed + 0,5 °C` / `Tinf = Tmed − 0,5 °C` (RNF07), derating linear
`α: 1 → 0` entre `Td = 45 °C` e `Tc = 60 °C`, limitadores `Ilim = min(Iperfil, Imax, IP, IV)`
(`IP`/`IV` derivados do modelo resistivo) e comando `Icmd = α·Ilim`, com prevalência de
`Icmd = 0` em bloqueio térmico (`Tsup ≥ Tc` ou `Tinf < Tmin = 10 °C`), falha (amostra
inválida/vencida, `V/I/P` medido acima do limite) ou fim de carga (`z ≥ 0,80`).
Rearme manual exige dados válidos + histerese de 2 °C (`Tsup ≤ 43`, `Tinf ≥ 12`).

---

## 2. Instalação

Pré-requisito: Python 3.10 ou superior.

```bash
# 1. Clone
git clone https://github.com/LordNoob404/AT05-Simulador.git
cd AT05-Simulador

# 2. Ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Dependências (todas open source)
pip install -r requirements.txt
```

## 3. Como executar

```bash
# Um cenário (ex.: C3 = 150 A com supervisão)
python run_simulation.py --scenario C3 --dt 0.1

# Todos os cenários de uma vez
python run_simulation.py --scenario ALL --dt 0.1

# Repetir a planta com passo fino (teste de convergência, critério interno ≤ 1 %)
python run_simulation.py --scenario C4 --dt 0.05

# Rodar a suíte de aceite
pytest tests/ -v
```

**Opções da CLI:** `--scenario {C1,C2,C3,C4,C4_sem_protecao,C5,C6,C7,ALL}` (padrão `ALL`),
`--dt` passo da planta em segundos (padrão `0.1`), `--sup-dt` período do supervisor
(padrão `1.0`).

## 4. Cenários e resultados esperados

| ID | Configuração | Pergunta que responde |
|---|---|---|
| C1 | 25 A; Ta = 25 °C | Referência de T, P, energia e tempo? |
| C2 | 150 A **sem** derating (virtual; termina CONCLUÍDO no nominal) | Efeito acadêmico da corrente alta? |
| C3 | 150 A **com** supervisão | Quanto o controle reduz Tmax e o tempo > Td? |
| C4 | T₀ = 44 °C, Ta = 40 °C, H: 50 → 25 W/K em t = 120 s (com/sem proteção) | Reação a calor + pior troca? |
| C5 | Injeções em Td/Tc ± 0,1 °C e abaixo de Tmin (+ fronteiras efetivas 44,5/59,5/10,5) | Fronteiras, bloqueio frio e rearme ok? |
| C6 | V/I/P acima do limite; amostra inválida/ausente/vencida; travamento | Falha em ≤ 2 s com causa registrada? |
| C7 | Limites via configuração; perda controlada de amostras | RNF05/RNF03 atendem? |

Resultados de referência (`dt = 0,1 s`, supervisor 1 s):

| Cenário | Tempo | Tmax | Tempo > Td¹ | Energia | Fim |
|---|---|---|---|---|---|
| C1 | 72,00 min | 26,06 °C | 0,00 min | 10,440 kWh | CONCLUIDO |
| C2 | 12,00 min | 38,06 °C | 0,00 min | 10,800 kWh | CONCLUIDO |
| C3 | 12,00 min | 38,06 °C | 0,00 min | 10,800 kWh | CONCLUIDO |
| C4 s/ proteção | 12,00 min | 57,44 °C | 11,57 min | 10,800 kWh | CONCLUIDO |
| C4 c/ supervisão | 18,03 min | 52,14 °C | 17,60 min | 10,670 kWh | CONCLUIDO |

¹ `tempo_acima_Td` usa **Tsup > Td** em todos os cenários (inclusive desprotegidos).
Leitura do C4: o derating reduz Tmax em 5,31 °C ao custo de +6,03 min.

## 5. Artefatos gerados (por cenário, em `outputs/<ID>/`)

- **`<ID>.csv`** — série temporal: `scenario,sequence,time_s,T_C,V_V,I_A,P_W,SOC,state,valid,alarm_code,Icmd_A`
  (lacunas indicadas explicitamente; nunca se repete medida como amostra nova).
- **`<ID>_metrics.json`** — `Tmax_C`, `tempo_acima_Td_min`, `tempo_carga_min`, `energia_kWh`,
  `registros_validos_pct` (RNF03 ≥ 99 %), `atraso_atuacao_s` (RNF02 ≤ 2 s), `conclusao`
  (`CONCLUIDO` ≠ interrompido por proteção).
- **`<ID>_T-P-SOC.png`** — T×t (com Td/Tc), P×t, SOC×t e Icmd×t, com unidades e legenda.

## 6. Testes (`pytest tests/ -v`, 9 passando)

`test_equacoes.py` (repouso I = 0; conferências 313,44 V/7836 W e 325,44 V/48816 W;
Joule 60/2160 W; equilíbrios 26,2/68,2/126,4 °C; tempos 4320/720 s) ·
`test_fronteiras.py` (pontos AT04 + fronteiras efetivas com margem + rearme com histerese) ·
`test_falhas.py` (C6 no mesmo ciclo; C7: config válida/incoerente, RNF03 98 % reprova / 99 % limiar) ·
`test_convergencia.py` (dt 0,1 × 0,05 sem arredondamento precoce; tabela de referência; artefatos C1–C7).

## 7. Decisões de implementação registradas

1. Supervisor a 1 s com ZOH; planta a 0,1 s; parada com tolerância numérica (`1e-9`, pois
   43200 somas de `1/72000` em IEEE-754 ficam ~7,7e-13 abaixo de 0,80).
2. Validação da amostra **antes** dos comparadores térmicos (defeito de sensor = FALHA,
   nunca BLOQUEIO térmico).
3. Causa primária do bloqueio/falha retida (*first-out latch*) até rearme manual.
4. `IP`/`IV` não limitam entre 20–80 % de SOC (limiares em z > 0,8472/0,875); a lógica é
   coberta por injeção em C6.
5. Energia decomposta em `E = Equim + Er` (`Equim = 10,368 kWh` constante) — explica por que
   só `+R` eleva o consumo na sensibilidade.

## 8. Estrutura dos arquivos

`model.py` (planta pura, sem I/O) · `supervisor.py` (BMS conceitual, sem I/O) ·
`scenarios.py` (C1–C7 como dados reproduzíveis) · `run_simulation.py` (CLI + loop + artefatos) ·
`plots.py` (gráficos) · `tests/` · `outputs/` (gerado, ignorado no git).

Licença MIT — ver `LICENSE`.
