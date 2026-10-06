# carcode: instructions for AI agents

carcode lets a person talk to Claude Code from their car: a Siri Shortcut sends speech to a small
server on their Mac, Claude Code does the work, and CarPlay reads the answer aloud.

If a user asks you to **install carcode**, follow the steps below in order. Run the commands
yourself; stop and ask the user only where it says **Ask the user** or **Hand over**.

## Install

1. **Check the platform.** carcode only runs on macOS. If `uname` is not `Darwin`, tell the user
   and stop.

2. **Check Claude Code.** Run `command -v claude`. If it is missing, tell the user to install it
   (`curl -fsSL https://claude.ai/install.sh | bash`) and log in by running `claude` once, then
   stop. You cannot log in for them.

3. **Ask the user** which folder holds their git repos (suggest `~/code` or whichever of
   `~/code`, `~/dev`, `~/projects`, `~/src` exists), what they want to call the assistant
   (default `Jarvis`; they will say "Hey Siri, Jarvis"), and how it should address them (default
   `Boss`). Ask before installing Homebrew packages if `uv` or `cloudflared` are missing.

4. **Run the installer** with their answers:

   ```bash
   npx --yes carcode-cli --yes --workdir "<repos folder>" --name "<name>" --title "<title>"
   ```

   If Node isn't available, use the same flags with the shell installer:
   `curl -fsSL https://raw.githubusercontent.com/Harsh-Rastogi-03/carcode/main/install.sh | bash -s -- --yes --workdir "<repos folder>" --name "<name>" --title "<title>"`.

   It installs `uv`/`cloudflared` with Homebrew if missing, keeps carcode in `~/.carcode` (npm)
   or `~/carcode` (curl), starts two background services (server and tunnel) with launchd, and
   builds the signed Siri Shortcut, opening it in the Shortcuts app.

5. **Verify** with `npx carcode-cli doctor --json` (or `./carcode doctor --json` in a clone). `"ready": true` means everything
   works. For any check that is not `ok`, run its `fix` command, then run doctor again. The public
   URL can take up to 30 seconds after install; wait and retry once before reporting a problem.

6. **Smoke test** with `npx carcode-cli say "what can you do?"` and read the reply to the user.

7. **Hand over** the two steps only a person can do:
   - In the Shortcuts window that opened, click **Add Shortcut**. It syncs to the iPhone through
     iCloud in about a minute.
   - On the iPhone: **Settings → Siri** → turn on **Allow Siri When Locked**, and set
     **Siri Responses** to **Prefer Spoken Responses**. Optionally **Accessibility → Siri → Siri
     Pause Time → Longest**.

   Then tell them to say **"Hey Siri, <name>"**, and that `npx carcode-cli talk` lets them try it
   out loud in the terminal right now, without a phone.

## Operate

Use `npx carcode-cli <command>` from anywhere for npm installs, or `./carcode <command>` in a clone.

| Task | Command |
|---|---|
| Health check (machine-readable) | `./carcode doctor --json` |
| Services, URL and dashboard link | `./carcode status` |
| Send one message | `./carcode say "…"` |
| Conversation in the terminal | `./carcode talk` (`--quiet` to skip speech) |
| Rebuild the shortcut after the URL changes | `./carcode shortcut` |
| Follow the log | `./carcode logs` |
| Update to the latest version | `npx carcode-cli@latest update` (or `./carcode update` in a clone) |
| Stop and remove the services | `./carcode uninstall` |

Settings live in `.env` in the carcode folder (`npx carcode-cli where` prints it). After editing it,
run `./carcode restart`.

## Rules

- Never print, paste or commit `data/token` or the `.shortcut` file: the token controls Claude Code
  on the user's Mac.
- Don't edit `prompts/assistant.md` safety rules unless the user asks.
- `data/` and `.env` are local and gitignored; leave them out of commits.

## Developing carcode

```bash
uv run --group dev pytest        # uses a fake Claude Code, no login needed
uv run --group dev ruff check .
bash -n carcode install.sh run_server.sh run_tunnel.sh
```
