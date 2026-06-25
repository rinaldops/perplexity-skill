#!/usr/bin/env python3
"""
Interface de consulta ao Perplexity (foco acadêmico por padrão).

Fluxo:
1. Abre o Perplexity num perfil persistente autenticado.
2. Seleciona o modo de FOCO (academic|web) ANTES de enviar a pergunta.
3. Digita a pergunta de forma humana e envia (Enter).
4. Aguarda a resposta por POLLING com heurística de estabilidade.
5. Extrai a lista de FONTES (título + URL) exibida pelo Perplexity.
6. Retorna: texto + seção "Fontes" + lembrete de follow-up.

Stateless: cada pergunta abre uma sessão nova (thread novo).

Abordagem híbrida de auth: perfil persistente + injeção de cookies de
state.json (workaround do bug do Playwright #36139).
"""

import argparse
import sys
import time
import re
from pathlib import Path
from urllib.parse import urlparse

from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from browser_utils import BrowserFactory, StealthUtils, check_cloudflare, CloudflareChallenge
from config import (
    PERPLEXITY_URL,
    FOCUS_URLS,
    QUERY_INPUT_SELECTORS,
    RESPONSE_SELECTORS,
    GENERATING_INDICATOR_SELECTORS,
    SOURCES_TAB_TEXT_PATTERN,
    QUERY_TIMEOUT_SECONDS,
    STABILITY_POLLS,
)


# Lembrete de follow-up — incentiva o Claude a aprofundar antes de responder ao usuário.
# Cada pergunta abre um thread novo (stateless), então a próxima pergunta deve carregar contexto.
FOLLOW_UP_REMINDER = (
    "\n\nIMPORTANTÍSSIMO: Isso é TUDO que você precisa saber? "
    "Você sempre pode fazer outra pergunta! Antes de responder ao usuário, "
    "revise o pedido original e esta resposta. Se algo ainda estiver incompleto, "
    "faça outra pergunta abrangente (cada pergunta abre um thread novo, então "
    "inclua todo o contexto necessário). E NUNCA invente referências: use apenas "
    "as fontes listadas abaixo."
)


def inspect_controls(page):
    """
    Modo de descoberta: lista botões/controles da página para acharmos o
    seletor do foco acadêmico (e outros). Imprime aria-label, texto e data-testid.
    """
    print("\n" + "=" * 60)
    print("🔎 INSPEÇÃO DE CONTROLES (para mapear seletores)")
    print("=" * 60)

    js = r"""
    () => {
        const out = [];
        const els = document.querySelectorAll('button, [role="button"], a[href], [data-testid]');
        els.forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;  // só visíveis
            out.push({
                tag: el.tagName.toLowerCase(),
                text: (el.innerText || '').trim().slice(0, 40),
                aria: el.getAttribute('aria-label') || '',
                testid: el.getAttribute('data-testid') || '',
                title: el.getAttribute('title') || '',
                href: el.getAttribute('href') || '',
            });
        });
        return out;
    }
    """
    try:
        items = page.evaluate(js)
    except Exception as e:
        print(f"  ❌ Falha ao inspecionar: {e}")
        return

    print(f"  {len(items)} controles visíveis encontrados:\n")
    for it in items:
        parts = []
        if it['text']:
            parts.append(f"text={it['text']!r}")
        if it['aria']:
            parts.append(f"aria={it['aria']!r}")
        if it['testid']:
            parts.append(f"testid={it['testid']!r}")
        if it['title']:
            parts.append(f"title={it['title']!r}")
        if it['href']:
            parts.append(f"href={it['href'][:40]!r}")
        print(f"  [{it['tag']}] " + " | ".join(parts))
    print("\n" + "=" * 60)


def _title_score(text: str, host: str) -> int:
    """
    Pontua o quão "título de verdade" um texto de âncora é, para escolher o
    melhor rótulo quando a mesma URL aparece em vários lugares:
    - Chip de citação (span.citation) -> texto = domínio (ex.: "scielo"): baixo.
    - Link de referência (dentro do texto) -> título completo: alto.
    """
    if not text:
        return 0
    base = host.split(':')[0].lower()
    low = text.lower()
    # Domínio-ish: sem espaço e contido no host -> é um chip de citação.
    if ' ' not in text and (low in base or base.startswith(low) or low in base.replace('www.', '')):
        return 1
    return 10 + len(text)


def _clean_title_from_anchor(raw: str) -> str:
    """
    Extrai o título do texto de uma âncora.
    Os cards do painel de fontes têm texto = "domínio\\nTítulo completo".
    Pegamos a 2ª linha em diante (o título). Chips de citação têm só o domínio.
    """
    parts = [p.strip() for p in re.split(r'[\r\n]+', raw or '') if p.strip()]
    if len(parts) >= 2:
        return re.sub(r'\s+', ' ', ' '.join(parts[1:]))  # pula a linha do domínio
    return re.sub(r'\s+', ' ', parts[0]) if parts else ''


def _open_sources_panel(page):
    """
    Clica no botão 'N sources' para abrir o painel com todos os cards de fonte
    (que trazem os títulos completos). Best-effort.
    """
    try:
        btn = page.get_by_text(re.compile(SOURCES_TAB_TEXT_PATTERN, re.I)).first
        if btn and btn.count() > 0:
            btn.click(timeout=4000)
            StealthUtils.random_delay(1200, 2200)
            return True
    except Exception:
        pass
    return False


def extract_sources(page) -> list:
    """
    Extrai fontes (título + URL) da resposta do Perplexity.

    Abre o painel 'N sources' (cards com título completo) e varre todas as
    âncoras externas. Para cada URL, escolhe o MELHOR título entre as âncoras
    (card > link de referência > chip de citação=domínio). Mantém a ordem de
    primeira aparição (espelha a numeração [n] das citações; fontes não citadas
    inline entram depois).

    Best-effort: se nada for encontrado, retorna lista vazia.
    """
    _open_sources_panel(page)

    try:
        anchors = page.query_selector_all('a[href^="http"]')
    except Exception:
        anchors = []

    order = []          # ordem de primeira aparição das URLs
    best_title = {}     # url -> melhor título encontrado
    best_score = {}     # url -> score do melhor título

    for a in anchors:
        try:
            href = a.get_attribute('href') or ''
            if not href.startswith('http'):
                continue
            host = urlparse(href).netloc.lower()
            if 'perplexity.ai' in host or not host:
                continue

            title = _clean_title_from_anchor(a.inner_text() or '')
            if not title:
                title = (a.get_attribute('aria-label') or '').strip()

            score = _title_score(title, host)

            if href not in best_title:
                order.append(href)
                best_title[href] = title
                best_score[href] = score
            elif score > best_score[href]:
                best_title[href] = title
                best_score[href] = score
        except Exception:
            continue

    sources = []
    for href in order:
        title = best_title.get(href) or urlparse(href).netloc
        sources.append({'title': title[:250], 'url': href})
    return sources


def format_sources(sources: list) -> str:
    if not sources:
        return (
            "\n\n## Fontes\n"
            "⚠️ Não foi possível extrair a lista de fontes desta resposta "
            "(os seletores de fontes podem precisar de ajuste — veja config.py). "
            "Verifique manualmente no Perplexity antes de citar referências."
        )
    lines = ["\n\n## Fontes"]
    for i, s in enumerate(sources, 1):
        lines.append(f"[{i}] {s['title']} — {s['url']}")
    return "\n".join(lines)


def ask_perplexity(question: str, focus: str = "academic", headless: bool = False,
                   inspect: bool = False) -> str:
    """Faz uma pergunta ao Perplexity e retorna a resposta + fontes + lembrete."""
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️ Não autenticado. Rode: python scripts/run.py auth_manager.py setup")
        return None

    print(f"💬 Pergunta: {question}")
    print(f"🎯 Foco: {focus}")

    playwright = None
    context = None

    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)

        page = context.new_page()
        start_url = FOCUS_URLS.get(focus, PERPLEXITY_URL)
        print(f"  🌐 Abrindo o Perplexity ({'busca acadêmica' if focus == 'academic' else 'busca web'})...")
        print(f"     {start_url}")
        page.goto(start_url, wait_until="domcontentloaded")

        # Detecta Cloudflare e falha com mensagem clara (não trava o polling).
        StealthUtils.random_delay(800, 1500)
        if check_cloudflare(page):
            raise CloudflareChallenge(
                "O Perplexity apresentou um challenge do Cloudflare. "
                "Rode com --show-browser e resolva manualmente, ou tente novamente mais tarde."
            )

        # Modo inspeção: lista controles e sai (descoberta de seletores).
        if inspect:
            StealthUtils.random_delay(1500, 2500)  # deixa a UI assentar
            inspect_controls(page)
            return "__INSPECT_DONE__"

        # Encontra o input.
        print("  ⏳ Procurando o campo de pergunta...")
        query_element = StealthUtils.find_first(page, QUERY_INPUT_SELECTORS, timeout_ms=15000)
        if not query_element:
            print("  ❌ Não encontrei o campo de pergunta (A VERIFICAR seletores em config.py).")
            return None

        # O foco já foi aplicado pela URL do vertical (ACADEMIC_URL/home).
        # Confirmação leve: avisa se não estamos na página acadêmica esperada.
        if focus == "academic" and "/academic" not in page.url:
            print(f"  ⚠️ Esperava a página acadêmica, mas a URL é {page.url}")
            print("     (a busca pode sair no modo padrão; verifique as fontes)")

        # Digita e envia.
        print("  ⌨️  Digitando a pergunta...")
        StealthUtils.human_type(query_element, question)

        print("  📤 Enviando...")
        page.keyboard.press("Enter")
        StealthUtils.random_delay(800, 1800)

        # Polling com heurística de estabilidade.
        print("  ⏳ Aguardando a resposta...")
        answer = None
        stable_count = 0
        last_text = None
        deadline = time.time() + QUERY_TIMEOUT_SECONDS

        while time.time() < deadline:
            # Se ainda está gerando (botão stop visível), espera.
            generating = False
            for sel in GENERATING_INDICATOR_SELECTORS:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        generating = True
                        break
                except Exception:
                    continue
            if generating:
                stable_count = 0
                time.sleep(1)
                continue

            # Lê o container da resposta mais recente.
            for selector in RESPONSE_SELECTORS:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        text = (elements[-1].inner_text() or '').strip()
                        if text:
                            if text == last_text:
                                stable_count += 1
                                if stable_count >= STABILITY_POLLS:
                                    answer = text
                                    break
                            else:
                                stable_count = 0
                                last_text = text
                except Exception:
                    continue

            if answer:
                break
            time.sleep(1)

        if not answer:
            print("  ❌ Timeout aguardando a resposta")
            return None

        print("  ✅ Resposta recebida! Extraindo fontes...")
        sources = extract_sources(page)
        print(f"  🔗 {len(sources)} fonte(s) extraída(s)")

        return answer + format_sources(sources) + FOLLOW_UP_REMINDER

    except CloudflareChallenge as e:
        print(f"  🛑 Cloudflare: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description='Consultar o Perplexity (foco acadêmico)')
    parser.add_argument('--question', help='Pergunta a fazer')
    parser.add_argument('--focus', choices=['academic', 'web'], default='academic',
                        help='Modo de foco (default: academic)')
    parser.add_argument('--show-browser', action='store_true',
                        help='(padrão) Mostra a janela do browser — necessário p/ passar o Cloudflare')
    parser.add_argument('--headless', action='store_true',
                        help='Tenta rodar SEM janela (geralmente cai no Cloudflare do Perplexity)')
    parser.add_argument('--inspect', action='store_true',
                        help='Modo descoberta: lista controles da página e sai (não envia pergunta)')

    args = parser.parse_args()

    if not args.inspect and not args.question:
        parser.error("--question é obrigatório (exceto no modo --inspect)")

    # Padrão: COM janela (headed). O Perplexity usa Cloudflare, que bloqueia o
    # modo headless. --headless é opt-in para experimentação.
    headless = args.headless

    answer = ask_perplexity(
        question=args.question or "",
        focus=args.focus,
        headless=headless,
        inspect=args.inspect,
    )

    if answer == "__INSPECT_DONE__":
        return 0

    if answer:
        print("\n" + "=" * 60)
        print(f"Pergunta: {args.question}")
        print("=" * 60)
        print()
        print(answer)
        print()
        print("=" * 60)
        return 0
    else:
        print("\n❌ Falha ao obter resposta")
        return 1


if __name__ == "__main__":
    sys.exit(main())
