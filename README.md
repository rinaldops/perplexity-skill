# Perplexity Skill for Claude Code

[![Versão](https://img.shields.io/badge/vers%C3%A3o-0.2.1-2E75B6)](CHANGELOG.md)
[![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-375623)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-1F3864)](requirements.txt)
[![CI](https://github.com/rinaldops/perplexity-skill/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

**Deixe o [Claude Code](https://github.com/anthropics/claude-code) consultar o Perplexity AI direto do terminal, com foco em busca acadêmica e respostas acompanhadas de FONTES verificáveis.**

Pensada para apoiar pesquisa comparada — confrontar ciência e filosofia acadêmica com a
Doutrina Espírita de Allan Kardec — sempre trazendo **referências reais (papers, artigos)
e nunca inventadas**.

> Automação de browser com Patchright (fork stealth do Playwright) + perfil de Chrome
> persistente + autenticação manual + extração de fontes do painel do Perplexity.

---

## ⚠️ Importante

- **Automação NÃO-oficial** do site do Perplexity. **Não** usa a API oficial (Sonar),
  porque a API não reproduz a busca acadêmica com lista de fontes da interface web.
- Sujeita aos **Termos de Serviço** do Perplexity e a **quebrar quando a UI mudar**
  (os seletores DOM podem precisar de ajuste — veja [Ajustando seletores](#ajustando-seletores)).
- Funciona **apenas no Claude Code local**, não na web UI (que roda skills em sandbox sem rede).
- Recomendado usar uma **conta dedicada** do Perplexity para automação.

---

## Instalação

```bash
# 1. Crie a pasta de skills (se não existir)
mkdir -p ~/.claude/skills

# 2. Clone este repositório para lá com o nome "perplexity"
cd ~/.claude/skills
git clone https://github.com/rinaldops/perplexity-skill perplexity

# 3. Abra o Claude Code e diga: "Quais skills eu tenho?"
```

No primeiro uso, a skill automaticamente:
- Cria um ambiente Python isolado (`.venv`)
- Instala as dependências
- Instala o **Google Chrome** para o Patchright (Chrome real, não Chromium — melhor contra
  o anti-bot Cloudflare do Perplexity)

Tudo fica contido na pasta da skill.

---

## Primeiro uso

### 1. Autentique (uma vez)

No Claude Code:
```
"Configure a autenticação do Perplexity"
```
ou direto:
```bash
python scripts/run.py auth_manager.py setup
```

- Uma janela do **Chrome abre visível**.
- Faça login no Perplexity (Google, Apple ou **e-mail com código**) — no seu ritmo.
- O setup **vigia a sessão** e salva sozinho assim que o login é concluído
  (`✅ Login confirmado`). Não precisa cronometrar ENTER.

> ⚠️ Se o login pelo **Google travar** (ele às vezes bloqueia OAuth em browser
> automatizado), use o **login por e-mail (código)** na mesma janela — funciona. Evite
> clicar no link do e-mail por fora: digite o **código** na janela do Perplexity, ou cole
> o link na barra de endereço **dessa** janela.

### 2. Pergunte

```bash
# Busca acadêmica (padrão) — retorna resposta + Fontes
python scripts/run.py ask_question.py --question "Há estudos revisados por pares sobre experiências de quase-morte e consciência?"

# Busca web geral
python scripts/run.py ask_question.py --question "..." --focus web

# Descoberta de seletores (lista controles da página e sai)
python scripts/run.py ask_question.py --inspect
```

A saída traz: **texto da resposta** + seção **"Fontes"** (`[n] Título — URL`) + um lembrete
de follow-up para o Claude aprofundar antes de te responder.

> ⚠️ **Uma janela do Chrome abre a cada pergunta** e fecha ao terminar. Isso é necessário:
> o Perplexity usa **Cloudflare**, que bloqueia o modo headless (sem janela). O foco
> acadêmico é feito navegando para o vertical `https://www.perplexity.ai/academic`.

---

## Requisitos

- **Windows / macOS / Linux** com Python 3.8+
- **Google Chrome** (instalado automaticamente pelo Patchright no setup)
- Uma **conta no Perplexity** (gratuita ou Pro)
- **Claude Code local** (não funciona na web UI)

---

## Comandos

| Comando | O que faz |
|---|---|
| `auth_manager.py setup` | Login manual (browser visível) |
| `auth_manager.py status` | Diz claramente se está autenticado |
| `auth_manager.py validate` | Testa a sessão salva (usa o cookie salvo; headless pode ser inconclusivo por Cloudflare) |
| `auth_manager.py reauth` | Limpa e refaz o login |
| `auth_manager.py clear` | Apaga os dados de autenticação |
| `ask_question.py --question "..."` | Consulta (foco acadêmico por padrão) |
| `ask_question.py --question "..." --focus web` | Consulta em busca web geral |
| `ask_question.py --inspect` | Lista controles da página (descoberta de seletores) |

Sempre via `python scripts/run.py <script> ...`.

---

## Como funciona

```
Sua pergunta → Claude chama o Perplexity (foco acadêmico) → resposta + fontes → Claude sintetiza com referências reais
```

1. Abre o Perplexity num perfil de Chrome persistente e autenticado.
2. **Navega para o vertical acadêmico** (`/academic`) — é assim que o foco é aplicado.
3. Digita a pergunta de forma humana (char a char) e envia.
4. Aguarda a resposta por **polling com heurística de estabilidade** (texto idêntico por
   N leituras seguidas = streaming terminou), com timeout.
5. Abre o painel **"N sources"** e **extrai todas as fontes** (título completo + URL).
6. Retorna texto + seção "Fontes" + lembrete de follow-up.

### Estrutura

```
~/.claude/skills/perplexity/
├── SKILL.md                  # Instruções para o Claude
├── README.md                 # Este arquivo
├── AUTHENTICATION.md         # Detalhes de autenticação
├── CHANGELOG.md
├── requirements.txt
├── scripts/
│   ├── run.py                # Wrapper (SEMPRE use este)
│   ├── setup_environment.py  # Cria venv + instala deps
│   ├── config.py             # Caminhos, SELETORES, timeouts
│   ├── browser_utils.py      # BrowserFactory + StealthUtils + Cloudflare
│   ├── auth_manager.py       # Login / status / reauth / clear
│   └── ask_question.py       # Comando principal
├── .venv/                    # Ambiente isolado (auto-criado)
└── data/                     # auth_info.json (gitignored)

# Perfil do Chrome + sessão (FORA do repo, em pasta local não-sincronizada):
%LOCALAPPDATA%\perplexity-skill\browser_state\   # Windows
```

---

## Ajustando seletores

O DOM do Perplexity **muda com o tempo**. Se a skill não achar o campo de pergunta ou as
fontes, ajuste os seletores em [`scripts/config.py`](scripts/config.py):

1. Rode `python scripts/run.py ask_question.py --inspect` — abre a página e **lista os
   controles visíveis** (tag, texto, `aria-label`, `data-testid`).
2. Identifique o seletor novo (campo de pergunta, botão "N sources", etc.).
3. Atualize a lista correspondente em `config.py` (mantenha os fallbacks e adicione um
   comentário datado).

Cada bloco de seletores tem um comentário com a data da última verificação.

---

## Limites da conta gratuita

- O Perplexity **gratuito** limita o número de buscas "Pro"/avançadas por dia (o foco
  acadêmico costuma consumir esse cota). Ao atingir o limite, o resultado pode cair para
  a busca rápida ou pedir upgrade.
- Se notar respostas sem fontes ou degradadas, verifique se o limite diário foi atingido.
- O limite e os nomes dos modos podem mudar — confira na sua conta.

---

## Segurança e privacidade

- A sessão autenticada (cookies/perfil do Chrome) fica em
  `%LOCALAPPDATA%\perplexity-skill\` — **fora do repo** e de pastas sincronizadas.
- `data/` (dentro do repo) guarda só `auth_info.json` e é **gitignored**.
- O Chrome roda **localmente**; suas credenciais não saem da sua máquina.
- ⚠️ **Não** coloque o perfil do Chrome numa pasta do OneDrive/Dropbox: o sync trava os
  bancos de sessão do Chrome e o login não grava (use `PERPLEXITY_SKILL_DATA_DIR` para
  customizar o local, se precisar).
- Use uma conta dedicada se preferir.

---

## Aviso

Ferramenta de automação de browser feita para uso pessoal de pesquisa. Apesar das técnicas
de humanização (digitação realista, delays), não há garantia de que o Perplexity não
detecte/sinalize uso automatizado. Use com discernimento, revise sempre as respostas e as
fontes antes de usá-las, e respeite os Termos de Serviço do Perplexity.

---

## Licença

[MIT](LICENSE) © Rinaldo Paulino de Souza
