#!/usr/bin/env python3
"""
Configuração de ambiente da Skill Perplexity.
Gerencia o ambiente virtual e as dependências automaticamente.
"""

import os
import sys
import subprocess
import venv
from pathlib import Path

# Roda sob o Python do sistema (Windows cp1252); garante UTF-8 para os emojis
# dos prints não quebrarem com UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


class SkillEnvironment:
    """Gerencia o ambiente virtual específico da skill."""

    def __init__(self):
        self.skill_dir = Path(__file__).parent.parent
        self.venv_dir = self.skill_dir / ".venv"
        self.requirements_file = self.skill_dir / "requirements.txt"

        if os.name == 'nt':  # Windows
            self.venv_python = self.venv_dir / "Scripts" / "python.exe"
            self.venv_pip = self.venv_dir / "Scripts" / "pip.exe"
        else:  # Unix/Linux/Mac
            self.venv_python = self.venv_dir / "bin" / "python"
            self.venv_pip = self.venv_dir / "bin" / "pip"

    def ensure_venv(self) -> bool:
        """Garante que o ambiente virtual exista e esteja configurado."""

        if self.is_in_skill_venv():
            print("✅ Já rodando no ambiente virtual da skill")
            return True

        if not self.venv_dir.exists():
            print(f"🔧 Criando ambiente virtual em {self.venv_dir.name}/")
            try:
                venv.create(self.venv_dir, with_pip=True)
                print("✅ Ambiente virtual criado")
            except Exception as e:
                print(f"❌ Falha ao criar venv: {e}")
                return False

        if self.requirements_file.exists():
            print("📦 Instalando dependências...")
            try:
                # Atualiza o pip primeiro usando `python -m pip` para que o
                # pip.exe não tente se substituir enquanto roda — falha no Windows.
                subprocess.run(
                    [str(self.venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                    check=True,
                    capture_output=True,
                    text=True
                )

                subprocess.run(
                    [str(self.venv_python), "-m", "pip", "install", "-r", str(self.requirements_file)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print("✅ Dependências instaladas")

                # Instala o Google Chrome para o Patchright (não Chromium!).
                # Chrome real dá confiabilidade entre plataformas e melhor
                # fingerprinting contra anti-bot (Cloudflare do Perplexity).
                print("🌐 Instalando Google Chrome para o Patchright...")
                try:
                    subprocess.run(
                        [str(self.venv_python), "-m", "patchright", "install", "chrome"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print("✅ Chrome instalado")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Aviso: falha ao instalar o Chrome: {e}")
                    print("   Talvez seja preciso rodar manualmente: python -m patchright install chrome")
                    print("   Chrome é obrigatório (não Chromium) para confiabilidade!")

                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Falha ao instalar dependências: {e}")
                print(f"   Saída: {e.output if hasattr(e, 'output') else 'Sem saída'}")
                return False
        else:
            print("⚠️ requirements.txt não encontrado, pulando instalação de dependências")
            return True

    def is_in_skill_venv(self) -> bool:
        """Verifica se já estamos rodando no venv da skill."""
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_path = Path(sys.prefix)
            return venv_path == self.venv_dir
        return False

    def get_python_executable(self) -> str:
        """Retorna o executável Python correto."""
        if self.venv_python.exists():
            return str(self.venv_python)
        return sys.executable

    def activate_instructions(self) -> str:
        """Instruções para ativação manual."""
        if os.name == 'nt':
            activate = self.venv_dir / "Scripts" / "activate.bat"
            return f"Rode: {activate}"
        else:
            activate = self.venv_dir / "bin" / "activate"
            return f"Rode: source {activate}"


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Configura o ambiente da skill Perplexity')
    parser.add_argument('--check', action='store_true', help='Verifica se o ambiente está configurado')
    args = parser.parse_args()

    env = SkillEnvironment()

    if args.check:
        if env.venv_dir.exists():
            print(f"✅ Ambiente virtual existe: {env.venv_dir}")
            print(f"   Python: {env.get_python_executable()}")
            print(f"   Para ativar manualmente: {env.activate_instructions()}")
        else:
            print("❌ Nenhum ambiente virtual encontrado")
            print("   Rode setup_environment.py para criá-lo")
        return 0

    if env.ensure_venv():
        print("\n✅ Ambiente pronto!")
        print(f"   Venv: {env.venv_dir}")
        print(f"   Python: {env.get_python_executable()}")
        print(f"\nPara ativar manualmente: {env.activate_instructions()}")
        return 0
    else:
        print("\n❌ Configuração do ambiente falhou")
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
