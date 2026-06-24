#!/usr/bin/env python3
"""
Runner universal para os scripts da skill Perplexity.
Garante que todo script rode com o ambiente virtual correto da skill.

NUNCA chame os scripts diretamente — sempre via:
    python scripts/run.py <script.py> [args...]
"""

import os
import sys
import subprocess
from pathlib import Path

# Este wrapper roda sob o Python do SISTEMA (não o do venv), que no Windows usa
# cp1252 — então os emojis dos prints abaixo (e do setup_environment, que é
# chamado como subprocesso) quebram com UnicodeEncodeError no primeiro uso.
# Forçamos UTF-8 na saída deste processo e propagamos para os subprocessos.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_venv_python() -> Path:
    """Retorna o executável Python do ambiente virtual da skill."""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"

    if os.name == 'nt':  # Windows
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:  # Unix/Linux/Mac
        venv_python = venv_dir / "bin" / "python"

    return venv_python


def ensure_venv() -> Path:
    """Garante que o ambiente virtual exista (cria via setup na primeira vez)."""
    skill_dir = Path(__file__).parent.parent
    venv_dir = skill_dir / ".venv"
    setup_script = skill_dir / "scripts" / "setup_environment.py"

    if not venv_dir.exists():
        print("🔧 Primeira execução: criando ambiente virtual...")
        print("   Isso pode levar um minuto...")

        result = subprocess.run([sys.executable, str(setup_script)])
        if result.returncode != 0:
            print("❌ Falha ao configurar o ambiente")
            sys.exit(1)

        print("✅ Ambiente pronto!")

    return get_venv_python()


def main():
    if len(sys.argv) < 2:
        print("Uso: python run.py <script.py> [args...]")
        print("\nScripts disponíveis:")
        print("  ask_question.py   - Consultar o Perplexity (busca acadêmica)")
        print("  auth_manager.py   - Gerenciar autenticação (login manual)")
        print("  setup_environment.py - Configurar o ambiente manualmente")
        sys.exit(1)

    script_name = sys.argv[1]
    script_args = sys.argv[2:]

    # Aceita tanto "scripts/script.py" quanto "script.py"
    if script_name.startswith('scripts/'):
        script_name = script_name[len('scripts/'):]

    if not script_name.endswith('.py'):
        script_name += '.py'

    skill_dir = Path(__file__).parent.parent
    script_path = skill_dir / "scripts" / script_name

    if not script_path.exists():
        print(f"❌ Script não encontrado: {script_name}")
        print(f"   Diretório de trabalho: {Path.cwd()}")
        print(f"   Diretório da skill: {skill_dir}")
        print(f"   Procurado em: {script_path}")
        sys.exit(1)

    venv_python = ensure_venv()

    cmd = [str(venv_python), str(script_path)] + script_args

    # Força UTF-8 para que emojis/Unicode no print não quebrem em consoles
    # Windows com codepage legada (cp1252) -> UnicodeEncodeError.
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
