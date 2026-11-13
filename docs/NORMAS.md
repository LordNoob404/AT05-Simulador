# Checklist de normas e recomendações técnicas (RNF06) — AT05 Equipe 3

> Estado geral: **nenhuma conformidade normativa integral é declarada**. Itens não
> demonstráveis por simulação constam como pendentes (AT04 §6.3–§6.5). A AT03 não
> enumera normas específicas; isto impede certificar nesta etapa.

| Item (fonte) | Aplicabilidade ao modelo virtual | Estado |
|---|---|---|
| IEC 61000 — compatibilidade eletromagnética (slides) | Citada só nos slides; AT04 declara que **não** é requisito da AT03 | **Não requisito** |
| Circuito equivalente + balanço concentrado + contagem (MathWorks Simscape, AT04 [4]) | Fundamenta o método; não fornece os valores didáticos | **Referência atendida** |
| Dependência do *lithium plating* (Rodrigues *et al.* 2020, AT04 [5]) | Fundamenta limites do discurso (menor T ⇏ menor plating) | **Referência atendida** |
| IEC 62660 / NBR IEC 62133 (células e sistemas de lítio) | Exigem ensaio físico de produto; fora do escopo virtual (AT02/AT03 §6) | **Não aplicável / Pendente p/ produto real** |
| ISO 26262 / IEC 61508 (segurança funcional) | Exigiriam hardware, ASIL/SIL e certificação; simulação não comprova | **Não aplicável / Pendente** |
| RNF06 — 100 % dos requisitos obrigatórios da matriz | Sem normas enumeradas na AT03 | **Pendente até definição** |
| RNF07 — erro da cadeia de T ±0,5 °C | Lógica com margens implementada; sem calibração física | **Pendente físico** |
| RNF08 — latência de apresentação ≤ 500 ms | Simulação acelerada não mede tempo real | **Pendente** |

Manutenção: ao definir normas aplicáveis, adicionar linha com requisito, evidência exigida e
estado (Atendido/Parcial/Pendente), sem excluir falhas do denominador.
