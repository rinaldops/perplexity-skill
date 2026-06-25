"""
Configuração da Skill Perplexity.
Centraliza constantes, seletores DOM e caminhos.

⚠️ SOBRE OS SELETORES
O DOM do Perplexity muda com frequência.
Os seletores abaixo são listas de FALLBACK: o código tenta cada um na ordem
até achar um que funcione. Cada bloco tem um comentário datado.

Durante o desenvolvimento, rode com --show-browser e inspecione o DOM AO VIVO
para confirmar/atualizar cada seletor. Marque com a data quando confirmar.

Última revisão dos seletores: 2026-06-24 (confirmados: placeholder "Explore" para /academic)
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# Caminhos
# ----------------------------------------------------------------------------
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"

# IMPORTANTE: o perfil VIVO do Chrome (cookies/sessão em bancos SQLite que ele
# escreve continuamente) NÃO pode ficar numa pasta sincronizada (OneDrive/Dropbox).
# O sync trava/corrompe os arquivos no meio da escrita -> login que nunca grava a
# sessão e janela travada. Por isso colocamos o browser_state num diretório LOCAL
# (%LOCALAPPDATA% no Windows), independente de onde o repo esteja.
#   - Override opcional via env PERPLEXITY_SKILL_DATA_DIR.
_local_base = os.environ.get("PERPLEXITY_SKILL_DATA_DIR")
if _local_base:
    LOCAL_DATA_DIR = Path(_local_base)
elif os.name == "nt":
    LOCAL_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "perplexity-skill"
else:
    LOCAL_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "perplexity-skill"

BROWSER_STATE_DIR = LOCAL_DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"

# ----------------------------------------------------------------------------
# URLs
# ----------------------------------------------------------------------------
PERPLEXITY_URL = "https://www.perplexity.ai"
PERPLEXITY_URL_PATTERN = r"^https://www\.perplexity\.ai/"

# Foco acadêmico (2026-06-24, CONFIRMADO via --inspect): a UI nova do Perplexity
# expõe "Academic" como um VERTICAL de topo (link href="/academic"), não mais como
# um dropdown de "Focus" ao lado do campo. Então selecionamos o foco navegando
# direto para a URL do vertical. 'web' usa a home (modo Search padrão).
ACADEMIC_URL = "https://www.perplexity.ai/academic"

FOCUS_URLS = {
    "academic": ACADEMIC_URL,
    "web": PERPLEXITY_URL,
}

# ----------------------------------------------------------------------------
# Seletores do Perplexity (2026-06-24 — A VERIFICAR ao vivo)
# ----------------------------------------------------------------------------

# Campo de entrada da pergunta.
# Perplexity historicamente usa um <textarea> com placeholder "Ask anything";
# em algumas versões é um contenteditable. Vários fallbacks por segurança.
QUERY_INPUT_SELECTORS = [
    'textarea[placeholder*="Explore"]',      # placeholder do vertical /academic
    'textarea[placeholder*="Ask"]',          # placeholder "Ask anything..."
    'textarea[placeholder*="Type"]',         # placeholder "Type / for search modes"
    'textarea[placeholder*="Pergunte"]',     # UI em pt-BR
    'textarea#ask-input',                     # id observado em algumas versões
    'textarea[autofocus]',
    'div[contenteditable="true"]',            # variante contenteditable
    'textarea',                               # último recurso
]

# Controle de FOCO / modo de busca (LEGADO / fallback).
# Na UI atual (2026-06) o foco acadêmico é feito via URL do vertical (ACADEMIC_URL),
# não por dropdown. Estes seletores ficam só como fallback caso a UI volte a ter
# um menu de "Focus" perto do input. Não são usados no caminho principal.
FOCUS_TRIGGER_SELECTORS = [
    'button[aria-label*="Focus" i]',
    'button[aria-label*="Foco" i]',
    'button[aria-label*="source" i]',
    'button[aria-label*="fonte" i]',
    'button[data-testid*="focus" i]',
]

# Itens do menu de foco, por modo. O texto é casado de forma case-insensitive.
# Mapeamos o valor de --focus para uma lista de rótulos prováveis (en + pt).
FOCUS_OPTION_LABELS = {
    "academic": ["Academic", "Acadêmico", "Academico", "Scholar", "Papers"],
    "web": ["Web", "Internet", "All", "Tudo"],
}

# Container da resposta gerada (texto principal).
# Perplexity renderiza markdown numa área "prose". Vários fallbacks.
RESPONSE_SELECTORS = [
    '[data-testid="answer"]',
    'div.prose',
    '[id^="markdown-content"]',
    'div[dir="auto"] .prose',
    'main .prose',
]

# Indicador de "gerando / streaming em andamento".
# Enquanto algum destes estiver visível, a resposta ainda não terminou.
# Tipicamente um botão de "parar" (stop) durante o streaming.
GENERATING_INDICATOR_SELECTORS = [
    'button[aria-label*="Stop" i]',
    'button[aria-label*="Parar" i]',
    'button[data-testid="stop-generating"]',
    '[aria-label*="generating" i]',
]

# FONTES (Sources) — 2026-06-24, CONFIRMADO via diagnóstico ao vivo.
# A extração é feita em scripts/ask_question.py (extract_sources):
#  1) Clica no botão "N sources" (texto casa a regex abaixo) para abrir o painel.
#  2) Cada card de fonte é uma âncora <a href externo> cujo innerText é
#     "domínio\nTítulo completo". O título é a 2ª linha em diante.
#  3) Os chips de citação inline (span.citation) têm só o domínio — descartados
#     em favor do título do card (ver _title_score).
# Não há um data-testid estável para o container; por isso varremos todas as
# âncoras externas e escolhemos o melhor título por URL.
SOURCES_TAB_TEXT_PATTERN = r'\d+\s*sources?'   # ex.: "15 sources"

# ----------------------------------------------------------------------------
# Indicadores de sessão autenticada (logado)
# ----------------------------------------------------------------------------
# Presença de QUALQUER um sugere que o usuário está logado. O Perplexity não
# muda de domínio ao logar, então usamos estes sinais (avatar/menu de conta).
# A VERIFICAR ao vivo.
LOGGED_IN_INDICATORS = [
    'button[aria-label*="Account" i]',
    'button[aria-label*="Conta" i]',
    'img[alt*="avatar" i]',
    'a[href*="/settings"]',
    '[data-testid="user-avatar"]',
]

# Indicadores de NÃO logado (botão de entrar). Presença sugere sessão anônima.
LOGGED_OUT_INDICATORS = [
    'button:has-text("Sign in")',
    'button:has-text("Log in")',
    'button:has-text("Entrar")',
    'a[href*="/sign-in"]',
]

# Sinal DEFINITIVO de login concluído: o Perplexity usa NextAuth e seta um
# cookie de sessão quando o login termina. Os cookies transitórios do fluxo
# OAuth (next-auth.state, next-auth.pkce.*, next-auth.callback-url) NÃO contam —
# eles aparecem mesmo com o login pela metade. Checamos por substring no nome.
SESSION_COOKIE_HINTS = [
    "next-auth.session-token",   # __Secure-next-auth.session-token (login OK)
    "__Secure-next-auth.session-token",
]

# ----------------------------------------------------------------------------
# Detecção de challenge anti-bot (Cloudflare)
# ----------------------------------------------------------------------------
# Se qualquer um destes aparecer, falhamos com mensagem clara em vez de travar.
CLOUDFLARE_INDICATORS = [
    'iframe[src*="challenges.cloudflare.com"]',
    'text="Verify you are human"',
    'text="Verifique se você é humano"',
    '#cf-challenge-running',
    'text="Checking your browser"',
]

# ----------------------------------------------------------------------------
# Configuração do browser
# ----------------------------------------------------------------------------
# IMPORTANTE (Patchright): a stealth é feita INTERNAMENTE. Passar flags como
# --disable-blink-features=AutomationControlled, --no-sandbox ou um user_agent
# customizado AUMENTA a detecção (e o Google trava o login OAuth). Por isso a
# config recomendada é MÍNIMA: channel="chrome", no_viewport=True, headed.
# Ref.: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python (Best Practices)
#
# --no-sandbox também causava o aviso "unsupported command-line flag" e era
# desnecessário no Windows. Removido.
BROWSER_ARGS = [
    '--no-first-run',
    '--no-default-browser-check',
]

# Não definir user_agent customizado: o Patchright usa o UA real do Chrome.
# Mantido como None de propósito.
USER_AGENT = None

# ----------------------------------------------------------------------------
# Timeouts
# ----------------------------------------------------------------------------
LOGIN_TIMEOUT_MINUTES = 10
QUERY_TIMEOUT_SECONDS = 120
PAGE_LOAD_TIMEOUT = 30000

# Estabilidade do streaming: nº de leituras idênticas seguidas para considerar
# que a resposta terminou.
STABILITY_POLLS = 3
