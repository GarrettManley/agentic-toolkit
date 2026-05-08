# Credential Handling

**Library**: Python `keyring` (cross-platform abstraction)
**Backend on Windows**: Windows Credential Manager (DPAPI-protected by user's Windows account)
**Schema reference**: `program.schema.json`'s `submission.auth_ref` is a `{service, username}` pair — never credentials inline.

## Resolution

`hooks/lib/credentials.py::get_credential(auth_ref)` →

```python
import keyring
def get_credential(auth_ref: dict) -> str:
    return keyring.get_password(auth_ref["service"], auth_ref["username"])
```

Returns the secret string. **Never logs the secret. Never writes it to disk.**

## Setup

`scripts/setup_credentials.py <venue>` is interactive:
- Prompts user for credential
- Stores via `keyring.set_password(service, username, secret)`
- Documents which credentials each venue needs

## Per-venue credentials

| Venue | Credential type | Stage 1 needed? |
|-------|-----------------|------------------|
| `ghsa` | None — uses `gh auth login` | No |
| `huntr` | API token | Stage 7 |
| `ibb-h1`, `h1` | API token + username | Stage 7 |
| `bugcrowd` | API token | Stage 7 |
| `intigriti` | API token | Stage 7 |
| `direct-maintainer` | Optional PGP key for encrypted email | Stage 7 |

**Stage 1 needs ZERO populated credentials.** The only Stage-1-active venue (`ghsa`) dispatches via `gh api` and uses the user's existing `gh` CLI auth. The keyring infrastructure is built and tested against fixture credentials only; real credentials are added in their respective Stages 2/7.

## Rotation

`keyring` makes rotation trivial: `keyring.set_password()` overwrites. No file edits, no service restarts. Document in this file when each credential was last rotated.

| Venue | Service name | Last rotated |
|-------|--------------|--------------|
| (none populated yet) | | |

## Security notes

1. **Never commit credentials.** PT-6 + G-2 hooks scan for common credential patterns; they will hard-block any commit that includes one.
2. **The override key (`~/.claude/sec-research-override-key`) is NOT a credential** in the keyring sense — it's a HMAC key. Stored as a file outside the repo. Generate via:

   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))" > $HOME\.claude\sec-research-override-key
   ```

   Loss of this file = no overrides until a new key is generated. By design.

3. **Plaintext credentials in `~/.claude/settings.json` should be migrated** to keyring. The `env.GITHUB_PERSONAL_ACCESS_TOKEN` field in that file is a known plaintext-credential anti-pattern; consider moving it to `keyring.set_password("github-pat", "<github-username>", "<token>")` and reading via `keyring.get_password()` in any script that needs it.
