#!/usr/bin/env python3
"""
Gerenciador de autenticação do Perplexity.
Cuida do login manual (Google/Apple/e-mail) e da persistência da sessão.

Abordagem híbrida de autenticação:
- Perfil de browser persistente (user_data_dir) para consistência de fingerprint.
- Injeção manual de cookies a partir de state.json (workaround do bug do
  Playwright #36139 para cookies de sessão).

Como o Perplexity NÃO muda de domínio ao logar, o setup vigia automaticamente o
cookie de sessão (NextAuth) e salva sozinho quando o login é concluído.
"""

import json
import time
import argparse
import shutil
import sys
from pathlib import Path
from typing import Dict, Any

from patchright.sync_api import sync_playwright, BrowserContext

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BROWSER_STATE_DIR,
    STATE_FILE,
    AUTH_INFO_FILE,
    DATA_DIR,
    PERPLEXITY_URL,
    LOGGED_IN_INDICATORS,
    LOGGED_OUT_INDICATORS,
    SESSION_COOKIE_HINTS,
)
from browser_utils import BrowserFactory, check_cloudflare


class AuthManager:
    """Gerencia autenticação e estado de browser do Perplexity."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)

        self.state_file = STATE_FILE
        self.auth_info_file = AUTH_INFO_FILE
        self.browser_state_dir = BROWSER_STATE_DIR

    # ------------------------------------------------------------------ status
    def is_authenticated(self) -> bool:
        """
        Verifica se há sessão salva COM cookie de sessão do Perplexity.
        Só a existência do state.json não basta — precisa do cookie NextAuth,
        senão é uma sessão anônima (login pela metade).
        """
        if not self.state_file.exists():
            return False

        if not self._state_has_session_cookie():
            return False

        age_days = (time.time() - self.state_file.stat().st_mtime) / 86400
        if age_days > 14:
            print(f"⚠️ Estado do browser tem {age_days:.1f} dias; pode precisar reautenticar")

        return True

    def _state_has_session_cookie(self) -> bool:
        """Lê state.json e confere se há cookie de sessão (login concluído)."""
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            for c in state.get('cookies', []):
                name = c.get('name', '')
                if any(hint in name for hint in SESSION_COOKIE_HINTS):
                    return True
        except Exception:
            pass
        return False

    def get_auth_info(self) -> Dict[str, Any]:
        info = {
            'authenticated': self.is_authenticated(),
            'state_file': str(self.state_file),
            'state_exists': self.state_file.exists(),
        }

        if self.auth_info_file.exists():
            try:
                with open(self.auth_info_file, 'r', encoding='utf-8') as f:
                    info.update(json.load(f))
            except Exception:
                pass

        if info['state_exists']:
            info['state_age_hours'] = (time.time() - self.state_file.stat().st_mtime) / 3600

        return info

    # ------------------------------------------------------------------- setup
    def setup_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        """
        Login interativo. O browser abre VISÍVEL para login manual.
        Preferir login com Google. Magic-link por e-mail é inviável de automatizar.
        """
        if headless:
            print("⚠️ Login exige browser visível. Ignorando --headless no setup.")
            headless = False

        print("🔐 Iniciando configuração de autenticação...")
        print("   Uma janela do Chrome vai abrir.")
        print("   Faça login no Perplexity (recomendado: 'Continue with Google').")

        playwright = None
        context = None

        try:
            playwright = sync_playwright().start()
            context = BrowserFactory.launch_persistent_context(playwright, headless=False)

            page = context.new_page()
            page.goto(PERPLEXITY_URL, wait_until="domcontentloaded")

            if check_cloudflare(page):
                print("  ⚠️ Cloudflare apresentou um challenge. Resolva-o manualmente na janela.")

            # Já logado? (cookie de sessão é o sinal definitivo)
            if self._has_session_cookie(context):
                print("  ✅ Já autenticado!")
                self._save_browser_state(context)
                self._save_auth_info()
                return True

            # Vigilância automática: você loga no seu ritmo e o script detecta
            # sozinho quando o cookie de sessão (NextAuth) aparecer. Sem depender
            # de ENTER no momento certo. Os cookies do meio do fluxo OAuth não
            # contam — login pela metade fica anônimo.
            print("\n  ⏳ Faça o login na janela do navegador (Google, Apple ou e-mail).")
            print("     Você pode logar no seu ritmo — estou vigiando a sessão.")
            print(f"     Aguardando até {timeout_minutes:.0f} min pela confirmação do login...")
            print("     (Quando o login terminar, salvo a sessão automaticamente.)\n")

            ok = False
            deadline = time.time() + timeout_minutes * 60
            announced = 0
            while time.time() < deadline:
                if self._has_session_cookie(context):
                    ok = True
                    break
                # feedback periódico a cada ~15s
                elapsed = int(time.time() - (deadline - timeout_minutes * 60))
                if elapsed // 15 > announced:
                    announced = elapsed // 15
                    print(f"     ... ainda aguardando o login ({elapsed}s)")
                time.sleep(2)

            if ok:
                print("  ✅ Login confirmado (cookie de sessão presente)!")
                self._save_browser_state(context)
                self._save_auth_info()
                return True
            else:
                print("  ❌ Tempo esgotado sem detectar a sessão (login não concluído).")
                print("     Nada foi salvo. Dicas:")
                print("     - Feche TODOS os Chrome abertos antes de tentar de novo (perfil travado).")
                print("     - Tente o login por e-mail (código) se o Google travar.")
                return False

        except Exception as e:
            print(f"  ❌ Erro: {e}")
            return False

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

    def _has_session_cookie(self, context) -> bool:
        """Sinal definitivo: cookie de sessão NextAuth do Perplexity presente."""
        try:
            for c in context.cookies():
                name = c.get('name', '')
                if any(hint in name for hint in SESSION_COOKIE_HINTS):
                    return True
        except Exception:
            pass
        return False

    def _wait_for_session_cookie(self, context, timeout_minutes: int) -> bool:
        deadline = time.time() + timeout_minutes * 60
        while time.time() < deadline:
            if self._has_session_cookie(context):
                return True
            time.sleep(2)
        return False

    def _looks_logged_in(self, page) -> bool:
        """Heurística: indicador de logado presente e nenhum de não-logado."""
        try:
            for sel in LOGGED_IN_INDICATORS:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return True
            # Se não há botão de "entrar" visível, provavelmente está logado.
            any_logged_out = False
            for sel in LOGGED_OUT_INDICATORS:
                try:
                    if page.query_selector(sel):
                        any_logged_out = True
                        break
                except Exception:
                    continue
            return not any_logged_out
        except Exception:
            return False

    # ------------------------------------------------------------------- save
    def _save_browser_state(self, context: BrowserContext):
        try:
            context.storage_state(path=str(self.state_file))
            print(f"  💾 Sessão salva em: {self.state_file}")
        except Exception as e:
            print(f"  ❌ Falha ao salvar a sessão: {e}")
            raise

    def _save_auth_info(self):
        try:
            info = {
                'authenticated_at': time.time(),
                'authenticated_at_iso': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(self.auth_info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------ clear
    def clear_auth(self) -> bool:
        print("🗑️ Limpando dados de autenticação...")
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                print("  ✅ Sessão removida")
            if self.auth_info_file.exists():
                self.auth_info_file.unlink()
                print("  ✅ Info de auth removida")
            if self.browser_state_dir.exists():
                shutil.rmtree(self.browser_state_dir)
                self.browser_state_dir.mkdir(parents=True, exist_ok=True)
                print("  ✅ Perfil de browser limpo")
            return True
        except Exception as e:
            print(f"  ❌ Erro ao limpar: {e}")
            return False

    def re_auth(self, headless: bool = False, timeout_minutes: int = 10) -> bool:
        print("🔄 Reautenticando...")
        self.clear_auth()
        return self.setup_auth(headless, timeout_minutes)

    # --------------------------------------------------------------- validate
    def validate_auth(self) -> bool:
        """Valida a sessão salva abrindo o Perplexity em headless."""
        if not self.is_authenticated():
            return False

        print("🔍 Validando autenticação...")
        playwright = None
        context = None
        try:
            playwright = sync_playwright().start()
            context = BrowserFactory.launch_persistent_context(playwright, headless=True)
            page = context.new_page()
            page.goto(PERPLEXITY_URL, wait_until="domcontentloaded", timeout=30000)

            if self._has_session_cookie(context) or self._looks_logged_in(page):
                print("  ✅ Autenticação válida")
                return True

            if check_cloudflare(page):
                # Headless quase sempre cai no Cloudflare; não é conclusivo.
                # Caímos para o cookie salvo em state.json como melhor evidência.
                if self._state_has_session_cookie():
                    print("  ⚠️ Cloudflare bloqueou o teste headless, mas há cookie de sessão salvo")
                    print("  ✅ Provavelmente válida (confirme com uma pergunta real)")
                    return True
                print("  ⚠️ Cloudflare bloqueou e não há cookie de sessão salvo")
                return False

            print("  ❌ Sessão parece inválida (não logado)")
            return False
        except Exception as e:
            print(f"  ❌ Validação falhou: {e}")
            return False
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
    parser = argparse.ArgumentParser(description='Gerenciar autenticação do Perplexity')
    subparsers = parser.add_subparsers(dest='command', help='Comandos')

    setup_parser = subparsers.add_parser('setup', help='Configurar autenticação (browser visível)')
    setup_parser.add_argument('--timeout', type=float, default=10, help='Timeout de login em minutos (default: 10)')

    subparsers.add_parser('status', help='Verificar status da autenticação')
    subparsers.add_parser('validate', help='Validar a sessão salva')
    subparsers.add_parser('clear', help='Limpar autenticação')

    reauth_parser = subparsers.add_parser('reauth', help='Reautenticar (clear + setup)')
    reauth_parser.add_argument('--timeout', type=float, default=10, help='Timeout de login em minutos (default: 10)')

    args = parser.parse_args()
    auth = AuthManager()

    if args.command == 'setup':
        if auth.setup_auth(timeout_minutes=args.timeout):
            print("\n✅ Autenticação configurada!")
            print("Agora você pode usar ask_question.py para consultar o Perplexity.")
        else:
            print("\n❌ Configuração de autenticação falhou")
            exit(1)

    elif args.command == 'status':
        info = auth.get_auth_info()
        print("\n🔐 Status da Autenticação:")
        print(f"  Autenticado: {'Sim' if info['authenticated'] else 'Não'}")
        if info.get('state_age_hours') is not None:
            print(f"  Idade da sessão: {info['state_age_hours']:.1f} horas")
        if info.get('authenticated_at_iso'):
            print(f"  Último login: {info['authenticated_at_iso']}")
        print(f"  Arquivo de sessão: {info['state_file']}")
        if not info['authenticated']:
            print("\n  👉 Rode: python scripts/run.py auth_manager.py setup")

    elif args.command == 'validate':
        if auth.validate_auth():
            print("Autenticação válida e funcionando")
        else:
            print("Autenticação inválida ou expirada")
            print("Rode: python scripts/run.py auth_manager.py setup")

    elif args.command == 'clear':
        if auth.clear_auth():
            print("Autenticação limpa")

    elif args.command == 'reauth':
        if auth.re_auth(timeout_minutes=args.timeout):
            print("\n✅ Reautenticação concluída!")
        else:
            print("\n❌ Reautenticação falhou")
            exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
