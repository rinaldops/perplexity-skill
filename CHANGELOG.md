# Changelog

Todas as mudanças relevantes desta skill.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e o projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-06-24

### Adicionado
- Versão inicial da skill Perplexity (automação de browser, não-oficial).
- Arquitetura da skill:
  - `run.py` — wrapper que cria o `.venv`, instala deps e injeta UTF-8.
  - `setup_environment.py` — cria venv, atualiza pip via `python -m pip`, instala Chrome.
  - `config.py` — caminhos, timeouts e **listas de seletores com fallback** (datadas).
  - `browser_utils.py` — `BrowserFactory` (perfil persistente + injeção de cookies),
    `StealthUtils` (digitação humana) e detecção de Cloudflare.
  - `auth_manager.py` — `setup`/`status`/`validate`/`reauth`/`clear` com login manual
    confirmado por ENTER (Perplexity não muda de domínio ao logar).
  - `ask_question.py` — consulta com **foco acadêmico por padrão**, polling de
    estabilidade, **extração de fontes** e lembrete de follow-up.
- Parâmetro `--focus academic|web` (default `academic`).
- Seção **"Fontes"** na saída (`[n] Título — URL`), com fallback explícito quando não
  for possível extrair.
- Correções de Windows desde o início: pip via `python -m pip`, `PYTHONUTF8`/
  `PYTHONIOENCODING`, caminhos via `pathlib` + detecção `os.name == 'nt'`.

## [0.2.0] - 2026-06-24

### Mudado
- **Perfil do Chrome movido para fora do repositório/OneDrive** → `%LOCALAPPDATA%\perplexity-skill\`
  (override por `PERPLEXITY_SKILL_DATA_DIR`). O sync do OneDrive travava os bancos SQLite de
  sessão do Chrome e o login nunca persistia. Causa raiz do "login travado na ampulheta".
- **Config do browser enxuta para o padrão Patchright**: removidos `--no-sandbox`,
  `--disable-blink-features=AutomationControlled` e o `user_agent` fixo (aumentavam a
  detecção e travavam o OAuth do Google). Mantido apenas `ignore_default_args=["--enable-automation"]`.
- **Foco acadêmico via URL do vertical** (`/academic`), em vez de dropdown de "Focus"
  (a UI atual do Perplexity não tem mais o dropdown). Confirmado via `--inspect`.
- **Padrão agora é COM janela** (headed): o Cloudflare do Perplexity bloqueia headless.
  Adicionado `--headless` opcional (experimental) e `--inspect` (descoberta de seletores).
- **Setup com vigia automático**: detecta o cookie de sessão NextAuth e salva sozinho
  (sem depender do ENTER no tempo certo). `status` só diz "Autenticado" se o cookie existir.

### Extração de fontes melhorada
- `extract_sources` agora **abre o painel "N sources"** e lê os cards (texto
  `"domínio\nTítulo"`), capturando **todas** as fontes com **título completo** — não só
  as citadas inline. Antes, parte saía só com o domínio.
- Heurística de melhor-título por URL (card > link de referência > chip de citação).

### Validado
- Busca acadêmica end-to-end: pergunta → `/academic` → resposta + **14 fontes reais**
  (SciELO / PubMed Central / periódicos) com `[n] Título completo — URL`.

### Conhecido
- Follow-up no mesmo thread (conversa contínua) fica para v2.
