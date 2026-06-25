"""
Utilitários de browser da Skill Perplexity.
Cuida do lançamento do browser, stealth e interações comuns.
"""

import json
import time
import random
from typing import Optional, List

from patchright.sync_api import Playwright, BrowserContext, Page
from config import (
    BROWSER_PROFILE_DIR,
    STATE_FILE,
    BROWSER_ARGS,
    USER_AGENT,
    CLOUDFLARE_INDICATORS,
)


class CloudflareChallenge(Exception):
    """Levantada quando o Perplexity apresenta um challenge anti-bot do Cloudflare."""
    pass


class BrowserFactory:
    """Fábrica de contextos de browser configurados."""

    @staticmethod
    def launch_persistent_context(
        playwright: Playwright,
        headless: bool = True,
        user_data_dir: str = str(BROWSER_PROFILE_DIR),
    ) -> BrowserContext:
        """
        Lança um contexto persistente seguindo a config MÍNIMA recomendada pelo
        Patchright (stealth interna). Evita flags/user_agent que aumentam a
        detecção e travam o login OAuth do Google.
        """
        kwargs = dict(
            user_data_dir=user_data_dir,
            channel="chrome",   # Chrome real (essencial p/ stealth e Cloudflare)
            headless=headless,
            no_viewport=True,
            # Remove a flag --enable-automation: tira a barra "controlado por
            # software de teste" E reduz a detecção (Google trava o OAuth quando
            # essa flag está ativa). Esta é a ÚNICA flag de automação que ajuda
            # ao ser REMOVIDA — diferente de --no-sandbox/--disable-blink, que
            # pioram quando ADICIONADAS.
            ignore_default_args=["--enable-automation"],
        )
        # Só passa args se houver algum (evita flags de automação por padrão).
        if BROWSER_ARGS:
            kwargs["args"] = BROWSER_ARGS
        # Só define user_agent se explicitamente configurado (None = usa o real).
        if USER_AGENT:
            kwargs["user_agent"] = USER_AGENT

        context = playwright.chromium.launch_persistent_context(**kwargs)

        # Workaround do bug do Playwright #36139: cookies de sessão (expires=-1)
        # não persistem no user_data_dir automaticamente; reinjetamos de state.json.
        BrowserFactory._inject_cookies(context)

        return context

    @staticmethod
    def _inject_cookies(context: BrowserContext):
        """Injeta cookies de state.json, se existir."""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    if 'cookies' in state and len(state['cookies']) > 0:
                        context.add_cookies(state['cookies'])
            except Exception as e:
                print(f"  ⚠️  Não foi possível carregar state.json: {e}")


def check_cloudflare(page: Page) -> bool:
    """
    Retorna True se a página atual parece ser um challenge do Cloudflare.
    Usado para falhar com mensagem clara em vez de travar no polling.
    """
    for selector in CLOUDFLARE_INDICATORS:
        try:
            if selector.startswith('text='):
                txt = selector[len('text='):].strip('"')
                if page.get_by_text(txt, exact=False).count() > 0:
                    return True
            else:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    return True
        except Exception:
            continue
    return False


class StealthUtils:
    """Interações com aparência humana."""

    @staticmethod
    def random_delay(min_ms: int = 100, max_ms: int = 500):
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))

    @staticmethod
    def find_first(page: Page, selectors: List[str], timeout_ms: int = 10000,
                   state: str = "visible") -> Optional[object]:
        """
        Tenta cada seletor sem espera primeiro (query_selector); se nenhum
        estiver presente ainda, aguarda o timeout_ms total pelo primeiro que
        aparecer, fazendo polling a cada 300 ms sobre todos os seletores.
        """
        # Passe rápido: sem espera, só verifica o que já está no DOM.
        for selector in selectors:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    print(f"  ✓ Seletor OK (rápido): {selector}")
                    return el
            except Exception:
                continue

        # Passe com polling: tenta todos os seletores em rodízio até o timeout.
        import time as _time
        deadline = _time.time() + timeout_ms / 1000
        while _time.time() < deadline:
            for selector in selectors:
                try:
                    el = page.query_selector(selector)
                    if el and el.is_visible():
                        print(f"  ✓ Seletor OK: {selector}")
                        return el
                except Exception:
                    continue
            _time.sleep(0.3)
        return None

    @staticmethod
    def human_type(element, text: str):
        """
        Preenche o campo via fill() (instantâneo, sem detecção) e digita
        apenas os últimos 3 caracteres lentamente para simular interação humana.
        """
        element.click()
        StealthUtils.random_delay(80, 200)
        if len(text) > 4:
            element.fill(text[:-3])
            StealthUtils.random_delay(50, 120)
            for char in text[-3:]:
                element.type(char, delay=random.uniform(40, 90))
        else:
            for char in text:
                element.type(char, delay=random.uniform(40, 90))
