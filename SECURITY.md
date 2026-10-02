# Security

carcode gives whoever holds your access token the ability to run Claude Code on your Mac, with your logins and tools. Treat the token like a password.

## Reporting a vulnerability

Please don't open a public issue. Use GitHub's private advisory form instead: **Security → Report a vulnerability** on this repository. Include steps to reproduce. You'll get a reply within a few days.

## Model

- **Authentication:** every request needs the `X-Carcode-Token` header, compared in constant time. The token is 192 bits of randomness, stored in `data/token` (mode 600, gitignored).
- **Exposure:** the server binds to `127.0.0.1` only. The Cloudflare tunnel is the only way in from outside.
- **Tool limits:** Claude Code runs with an explicit allowlist (`--allowedTools`) and `acceptEdits`. Anything outside the list is denied, because nobody is there to approve it. The default list includes `python3`, `node` and package managers, which can run arbitrary code; narrow it with `CARCODE_ALLOWED_TOOLS`.
- **Outward actions:** messages, emails, merges, approvals and deletions require a spoken read-back and "confirm". This is enforced by the system prompt, not by code.
- **Prompt injection:** the prompt tells Claude to treat PR, issue, email and Slack text as data. For more safety, keep risky connectors out of the allowlist.

## If your token leaks

```bash
rm data/token && ./carcode restart && ./carcode shortcut
```

Then delete the old shortcut on every device.
