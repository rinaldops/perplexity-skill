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
        Tenta cada seletor da lista até achar um elemento. Retorna o handle
        do elemento e imprime qual seletor funcionou (útil para debug ao vivo).
        """
        for selector in selectors:
            try:
                el = page.wait_for_selector(selector, timeout=timeout_ms, state=state)
                if el:
                    print(f"  ✓ Seletor OK: {selector}")
                    return el
            except Exception:
                continue
        return None

    @staticmethod
    def human_type(element, text: str):
        """
        Digita caractere a caractere com velocidade humana.
        Funciona tanto em <textarea>/<input> quanto em contenteditable
        (o .type() do Patchright lida com ambos no elemento focado).
        """
        element.click()
        StealthUtils.random_delay(100, 300)
        for char in text:
            element.type(char, delay=random.uniform(25, 75))
            if random.random() < 0.05:
                time.sleep(random.uniform(0.15, 0.4))
