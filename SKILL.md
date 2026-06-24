---
name: perplexity
description: Consulte o Perplexity AI direto do Claude Code para respostas acadêmicas com FONTES verificáveis (papers, artigos). Foco acadêmico por padrão, automação de browser stealth, autenticação persistente. Ideal para confrontar ciência e filosofia acadêmica com a Doutrina Espírita de Allan Kardec — sempre com referências reais, nunca inventadas.
---

# Perplexity Skill for Claude Code

Consulta o Perplexity AI por automação de browser, com **foco acadêmico** por padrão.
Cada pergunta abre uma sessão nova (thread novo), busca em fontes acadêmicas, e retorna
a resposta **acompanhada de uma lista de fontes (título + URL)**.

Valor central: trazer respostas **com fontes verificáveis** para pesquisa comparada —
ciência e filosofia acadêmica vs. Espiritismo. **NUNCA inventar referências**: cite
apenas as fontes que a skill retornar na seção "Fontes".

> ⚠️ Esta skill usa automação **NÃO-oficial** do site do Perplexity (não a API Sonar).
> A API oficial não reproduz a busca acadêmica com lista de fontes da interface web.

## Papéis: Perplexity × Claude

Divisão de trabalho clara (detalhes em [`references/metodologia_pesquisa.md`](references/metodologia_pesquisa.md)):

- **Perplexity (esta skill) = o BUSCADOR com fontes.** Busca acadêmica ao vivo e entrega
  respostas ancoradas em fontes verificáveis. É a única ponte do projeto com a literatura
  atual/revisada por pares.
- **Claude (você) = o SINTETIZADOR e COMPARADOR.** Formula boas perguntas, faz follow-ups,
  sintetiza com nível de confiança e **compara os achados com a Doutrina Espírita** (onde
  convergem, divergem, ou a ciência é silente). **Disciplina anti-alucinação:** só cita as
  fontes retornadas; nunca inventa referências; rotula interpretação própria vs. fato com fonte.

Para pesquisa comparada, consulte também os **tiers de fonte**, os **níveis de confiança** e o
**template "Brief Comparado: Ciência/Filosofia × Kardec"** no arquivo de metodologia acima.

## Quando usar esta skill

Acione quando o usuário:
- Mencionar "Perplexity" explicitamente
- Pedir busca **acadêmica/científica/filosófica** com fontes (papers, artigos)
- Quiser confrontar ciência/filosofia acadêmica com a Doutrina Espírita
- Pedir referências verificáveis sobre um tema
- Usar frases como "pesquise no Perplexity", "busca acadêmica", "ache papers sobre..."

## CRÍTICO: sempre use o wrapper run.py

**NUNCA chame os scripts diretamente. SEMPRE use `python scripts/run.py [script]`:**

```bash
# ✅ CORRETO:
python scripts/run.py auth_manager.py status
python scripts/run.py ask_question.py --question "..."

# ❌ ERRADO (falha sem o venv):
python scripts/ask_question.py --question "..."
```

O `run.py` automaticamente:
1. Cria o `.venv` se necessário
2. Instala as dependências (e o Chrome do Patchright)
3. Injeta `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` (evita erro de Unicode no Windows)
4. Executa o script com o Python do venv

## Fluxo principal

### 1. Verificar autenticação
```bash
python scripts/run.py auth_manager.py status
```

### 2. Autenticar (uma vez, browser visível)
```bash
python scripts/run.py auth_manager.py setup
```
- O Chrome abre **visível** para login manual.
- **Recomende ao usuário "Continue with Google".**
- Após logar, o usuário **pressiona ENTER no console** para salvar a sessão.
- ⚠️ Magic-link por e-mail é **inviável de automatizar** — prefira Google/Apple.

### 3. Perguntar (foco acadêmico por padrão)
```bash
# Busca acadêmica (default) — abre uma janela do Chrome (necessário p/ Cloudflare)
python scripts/run.py ask_question.py --question "Sua pergunta aqui"

# Busca web geral
python scripts/run.py ask_question.py --question "..." --focus web

# Modo descoberta de seletores (lista controles da página e sai)
python scripts/run.py ask_question.py --inspect
```

> ⚠️ **Uma janela do Chrome abre a cada pergunta.** Isso é necessário: o Perplexity usa
> Cloudflare, que **bloqueia o modo headless**. Existe um `--headless` opcional, mas ele
> normalmente cai no challenge do Cloudflare — use só para experimentar.

## Saída

A resposta retorna em três partes:
1. **Texto da resposta** do Perplexity
2. **Seção "Fontes"** no formato `[n] Título — URL`
3. **Lembrete de follow-up** (veja abaixo)

Se as fontes não puderem ser extraídas, a seção "Fontes" avisa explicitamente —
nesse caso, **não cite referências** sem conferir manualmente.

## Mecanismo de follow-up (importante)

Toda resposta termina com: **"IMPORTANTÍSSIMO: Isso é TUDO que você precisa saber?"**

Comportamento esperado do Claude:
1. **PARE** — não responda imediatamente ao usuário
2. **ANALISE** — compare a resposta ao pedido original
3. **IDENTIFIQUE LACUNAS** — falta algo? (cada pergunta é um thread novo, sem contexto)
4. **PERGUNTE DE NOVO** — se houver lacuna, faça outra pergunta abrangente (com todo o contexto)
5. **REPITA** até a informação estar completa
6. **SINTETIZE** — combine as respostas antes de responder ao usuário
7. **CITE APENAS AS FONTES LISTADAS** — nunca invente referências

## Referência de comandos

### Autenticação (`auth_manager.py`)
```bash
python scripts/run.py auth_manager.py setup     # Configurar (browser visível, login manual)
python scripts/run.py auth_manager.py status    # Ver status
python scripts/run.py auth_manager.py validate  # Validar sessão salva
python scripts/run.py auth_manager.py reauth    # Reautenticar (clear + setup)
python scripts/run.py auth_manager.py clear      # Limpar autenticação
```

### Pergunta (`ask_question.py`)
```bash
python scripts/run.py ask_question.py --question "..." [--focus academic|web] [--headless] [--inspect]
```

## Foco acadêmico

- O **default é `academic`**: a skill navega direto para o **vertical acadêmico** do
  Perplexity (`https://www.perplexity.ai/academic`) e pergunta ali — busca em fontes
  acadêmicas (papers/artigos).
- `--focus web` usa a home (busca web geral).
- Se a UI do Perplexity mudar e a página `/academic` deixar de ter campo de busca, a skill
  avisa. Para investigar o DOM ao vivo, rode `--inspect` (lista os controles da página) e
  ajuste `FOCUS_URLS`/seletores em `scripts/config.py`.

## Armazenamento de dados

- `data/auth_info.json` (dentro da skill) — metadados de autenticação (data do login).
- **Perfil do Chrome + sessão** ficam em `%LOCALAPPDATA%\perplexity-skill\browser_state\`
  (Windows) — **fora** da skill e fora de qualquer pasta sincronizada.
  - Por quê: o Chrome escreve a sessão em bancos SQLite continuamente; se isso ficar numa
    pasta do OneDrive/Dropbox, o sync trava/corrompe os arquivos e o **login nunca grava**.
  - Override opcional: variável de ambiente `PERPLEXITY_SKILL_DATA_DIR`.

**Segurança:** `data/` é protegido por `.gitignore`; o perfil local nunca entra no repo.

## Troubleshooting

| Problema | Solução |
|---------|----------|
| ModuleNotFoundError | Use o wrapper `run.py` |
| Login trava na ampulheta / não grava | Perfil em pasta sincronizada (OneDrive). Já resolvido: perfil vai p/ `%LOCALAPPDATA%`. Feche Chrome zumbis antes de reautenticar |
| "campo não encontrado" / só acha "Cloudflare" | Rodou `--headless`? O Cloudflare bloqueia headless. Rode no modo padrão (com janela) |
| Falha na autenticação | Login é manual com janela; se o Google travar, use login por **e-mail (código)** |
| Não acha o input / fontes | Seletores mudaram — rode `--inspect` e ajuste `config.py` |
| UnicodeEncodeError | Sempre use `run.py` (injeta UTF-8) |
| Sessão expirada | `python scripts/run.py auth_manager.py reauth` |

## Limitações

- Sem persistência de thread (cada pergunta = sessão nova/stateless)
- Conta gratuita tem limite diário de buscas Pro/acadêmicas (ver README)
- Automação **não-oficial**: sujeita aos ToS do Perplexity e a quebrar com mudanças de UI
- Só funciona no Claude Code **local** (não no sandbox da web UI)

## Boas práticas

1. **Sempre use run.py** — cuida do ambiente automaticamente
2. **Cheque a auth antes** de qualquer consulta
3. **Faça follow-ups** — não pare na primeira resposta
4. **Inclua todo o contexto** em cada pergunta (são independentes)
5. **Cite apenas as fontes retornadas** — nunca invente referências
6. **Sintetize** múltiplas respostas antes de responder ao usuário
