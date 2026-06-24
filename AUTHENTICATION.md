# Autenticação

Como a skill autentica no Perplexity e o que fica salvo.

## Abordagem

Usamos uma **abordagem híbrida**:

1. **Perfil de browser persistente** (`user_data_dir`) — mantém o fingerprint do Chrome
   consistente entre execuções (importante contra o Cloudflare do Perplexity).
2. **Injeção manual de cookies** a partir de `state.json` — workaround do bug do
   Playwright [#36139](https://github.com/microsoft/playwright/issues/36139): cookies de
   sessão (`expires=-1`) não persistem sozinhos no `user_data_dir`.

## Como o login é detectado

O **Perplexity não muda de domínio** ao logar (você continua em `perplexity.ai`). Por isso
detectamos o login por um sinal **definitivo**: o cookie de sessão do Perplexity (NextAuth,
`__Secure-next-auth.session-token`).

- O `setup` abre o browser **visível** e **vigia a sessão automaticamente**: você loga no
  seu ritmo (Google, Apple ou e-mail) e, assim que o cookie de sessão aparece, a sessão é
  salva sozinha — sem precisar cronometrar um ENTER.
- Os cookies transitórios do meio do fluxo OAuth (`next-auth.state`, `next-auth.pkce.*`,
  `next-auth.callback-url`) **não contam**: se o login parar na metade, a sessão fica
  anônima e nada é salvo. O `status` também checa o cookie de sessão antes de dizer
  "Autenticado: Sim".

## Onde a sessão é salva (IMPORTANTE)

O perfil **vivo** do Chrome (`user_data_dir`) e o `state.json` ficam em um diretório
**local**, fora do repositório e de pastas sincronizadas:

- Windows: `%LOCALAPPDATA%\perplexity-skill\browser_state\`
- Linux/Mac: `~/.local/share/perplexity-skill/browser_state/`
- Override: variável `PERPLEXITY_SKILL_DATA_DIR`.

Motivo: o Chrome grava a sessão em bancos SQLite continuamente. Se isso ficar numa pasta
do OneDrive/Dropbox, o sync trava/corrompe os arquivos e o **login nunca persiste** (janela
travada na ampulheta). Esse foi um bug real durante o desenvolvimento, resolvido movendo o
perfil para fora do OneDrive.

Se o login travar: feche **todos** os Chrome abertos (um processo zumbi pode estar segurando
o perfil) e rode `auth_manager.py setup` de novo.

## Métodos de login

| Método | Suportado | Observação |
|---|---|---|
| **Google** | ✅ Recomendado | Mais simples no fluxo manual |
| **Apple** | ✅ | Funciona no login manual |
| **E-mail (magic link)** | ⚠️ Inviável de automatizar | O link chega no e-mail e exige outra aba/cliente; não dá para automatizar de forma confiável |

## Comandos

```bash
python scripts/run.py auth_manager.py setup      # Login manual (browser visível)
python scripts/run.py auth_manager.py status     # Está autenticado?
python scripts/run.py auth_manager.py validate   # Testa a sessão (headless)
python scripts/run.py auth_manager.py reauth     # clear + setup
python scripts/run.py auth_manager.py clear      # Apaga a sessão
```

## O que é salvo (e onde)

- `%LOCALAPPDATA%\perplexity-skill\browser_state\browser_profile\` — perfil do Chrome
- `%LOCALAPPDATA%\perplexity-skill\browser_state\state.json` — cookies/localStorage
- `data/auth_info.json` (dentro da skill) — metadados (data do último login)

A sessão é considerada "velha" após ~14 dias (aviso, não bloqueio). Se as consultas
começarem a falhar por sessão expirada, rode `reauth`.

## Cloudflare

O Perplexity usa Cloudflare. A stealth do Patchright + Chrome real ajudam, mas se um
challenge aparecer:

- No `setup`/`--show-browser`: resolva manualmente na janela.
- Em headless: a skill **falha com mensagem clara** em vez de travar. Tente novamente com
  `--show-browser` ou mais tarde.

## Segurança

- `data/` nunca deve ser commitado (já está no `.gitignore`).
- O Chrome roda localmente; credenciais não saem da máquina.
