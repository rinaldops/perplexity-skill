# Metodologia de pesquisa — Perplexity × Claude na comparação com a Doutrina Espírita

Destilado de boas práticas para usar esta skill em pesquisa acadêmica comparada,
confrontando ciência e filosofia acadêmica com a Doutrina Espírita de Allan Kardec.

Princípio inegociável do projeto: **NUNCA inventar referências.** Só se cita o que o
Perplexity retornou na seção "Fontes" e que foi conferido.

> Nota: esta skill dirige a interface WEB do Perplexity por automação de browser. Não há
> API de ferramentas envolvida — as fontes vêm do painel de fontes da própria interface.

---

## 1. Divisão de papéis: quem faz o quê

Cada IA assume um papel distinto. Não confundir as funções.

### Perplexity (via esta skill) — o BUSCADOR com fontes
- Busca acadêmica ao vivo (papers, artigos) com `--focus academic`.
- Entrega **respostas ancoradas em fontes verificáveis** (a seção "Fontes").
- É a única ponte deste projeto com a literatura atual e revisada por pares.
- **Não** é onde se faz a síntese filosófica nem a comparação doutrinária.

### Claude (você) — o SINTETIZADOR e COMPARADOR
- Formula perguntas boas e abrangentes (cada pergunta é um thread novo/stateless).
- Faz **follow-ups** até cobrir a lacuna (ver mecanismo no SKILL.md).
- **Sintetiza** as respostas do Perplexity em afirmações claras, com nível de confiança.
- **Compara** os achados acadêmicos com a Doutrina Espírita: onde convergem, onde
  divergem, onde a ciência é silente, onde Kardec faz afirmações testáveis ou não.
- **Disciplina anti-alucinação**: só cita as fontes retornadas; nunca preenche lacunas
  com referências inventadas; marca o que é interpretação própria vs. o que tem fonte.

Regra de ouro: **fato acadêmico vem do Perplexity com URL; leitura espírita e
comparação vêm de Kardec/obras citadas explicitamente; a ponte entre os dois é
trabalho do Claude, sempre rotulada como tal.**

---

## 2. Fluxo de uma pergunta comparada

1. **Formule a pergunta acadêmica** isolando o ponto a investigar (não misture com a
   tese espírita ainda). Ex.: "Há estudos revisados por pares sobre correlação entre
   atividade cerebral e relatos de experiências de quase-morte?"
2. **Rode no foco acadêmico** (`--focus academic`).
3. **Cross-referencing**: um fato citado por **uma única fonte é provisório**. Se for
   central à comparação, faça um follow-up pedindo confirmação independente.
4. **Registre a afirmação** com nível de confiança (ver §4) e a(s) URL(s).
5. **Só então** traga a Doutrina Espírita: confronte o achado com o que Kardec diz
   (cite a obra/capítulo/item específico).
6. **Sintetize** no template comparado (§5).

---

## 3. Hierarquia de fontes (tier de confiança)

Priorize sempre os tiers altos. Nunca baseie uma afirmação central só em tier 6–8.

| Tier | Tipo | Confiança | Exemplos |
|---|---|---|---|
| 1 | Meta-análise / revisão sistemática revisada por pares | Máxima | Cochrane, revisões em periódicos de alto fator |
| 2 | Estudo primário revisado por pares | Muito alta | Nature, Lancet, NEJM, etc. |
| 3 | Dado institucional/governamental | Alta | OMS, IBGE, agências oficiais |
| 4 | Reportagem primária séria | Média-alta | Veículos de referência, reportagem original |
| 5 | Relatórios de indústria/think tanks | Média | Relatórios analíticos |
| 6 | Blog/newsletter de especialista | Média-baixa | Especialista identificável |
| 7 | Blog/fórum geral | Baixa | Medium, Reddit |
| 8 | Post de rede social | Muito baixa | X/Twitter, Facebook |

Para temas de fronteira (consciência, EQM, mediunidade, etc.), espere **muita
divergência** e literatura de qualidade variável: seja rigoroso com o tier e honesto
sobre o estado contestado do conhecimento.

---

## 4. Níveis de confiança de uma afirmação

Rotule cada afirmação sintetizada:

- **Alta**: múltiplas fontes primárias independentes concordam (tier 1–2).
- **Média**: uma fonte primária; ou várias secundárias concordando.
- **Baixa**: fonte única secundária; ou as fontes se contradizem.
- **Não verificado**: afirmado mas ainda sem fonte — exige follow-up antes de usar.

Vale tanto para afirmações da ciência quanto para o que se atribui à Doutrina: cite o
item de Kardec; não generalize "o Espiritismo diz" sem referência à obra.

---

## 5. Template — Brief Comparado: Ciência/Filosofia × Kardec

```markdown
# Brief Comparado: [Tema]
Data: [data]  ·  Confiança geral: Alta / Média / Baixa

## Pergunta
[O ponto específico investigado]

## Achados acadêmicos (via Perplexity)
### Achado 1: [rótulo]
- Afirmação: [enunciado preciso]
- Fontes: [n] Título — URL  (tier: __)
- Confiança: Alta / Média / Baixa
- Ressalva: [limitações]

## Posição da Doutrina Espírita
- O que Kardec afirma: [enunciado]
- Referência: [obra, cap./item — ex.: O Livro dos Espíritos, q. 0]

## Confronto
- **Convergências**: [onde ciência e Doutrina se alinham]
- **Divergências**: [onde conflitam, com a força da evidência de cada lado]
- **Silêncios**: [onde a ciência não se pronuncia / onde a Doutrina não detalha]
- **Testabilidade**: [a afirmação espírita é empiricamente testável? como?]

## Síntese do Claude (interpretação própria, sem fonte nova)
[Leitura integrada — claramente rotulada como interpretação, não como fato com fonte]

## Questões em aberto
- [ ] [O que exige mais pesquisa / follow-up no Perplexity]
```

---

## 6. Anti-padrões (não fazer)

- ❌ Inventar ou "lembrar" referências que o Perplexity não retornou.
- ❌ Misturar interpretação própria com afirmação factual sem rotular.
- ❌ Tratar fonte tier 6–8 como prova de um ponto central.
- ❌ Generalizar "a ciência prova" / "o Espiritismo afirma" sem citar o item específico.
- ❌ Parar na primeira resposta quando há lacuna óbvia — faça follow-up.
- ❌ Apresentar achado de fonte única como estabelecido (é provisório até confirmar).
