# Changelog

## 1.2.0

- **Answers stay in step.** When Claude Code finished a background task, its extra reply sat
  unread and every later answer came one question late. carcode now clears it before each new
  question, and the dashboard shows it as "finished in background".
- **Fewer cut-offs.** More half-sentences are held with "Go on." and joined with what you say
  next: endings like "the latest", "currently", "what you" or "did I", and a lone verb such as
  "Ask" or "Read".
- **Dashboard shows the joins.** Held half-sentences are marked, and joined turns show the full
  sentence that was sent to Claude Code.
- **A URL that never changes.** Set `CARCODE_TUNNEL_NAME` and `CARCODE_TUNNEL_HOSTNAME` to run a
  named Cloudflare tunnel on your own domain, so the URL and the Siri Shortcut survive restarts.

## 1.1.1

- **New home page.** carcode now has its own page at
  [harshrastogi.tech/carcode](https://www.harshrastogi.tech/carcode), with a live demo you can
  listen to. The npm package and README point there.

## 1.1.0

- **On npm.** `npx carcode-cli` runs the guided installer; `npx carcode-cli <command>` runs any command
  from anywhere. Files live in `~/.carcode`, and `npx carcode-cli@latest update` upgrades without
  touching your settings or token.
- **One-line installer.** `curl -fsSL https://raw.githubusercontent.com/Harsh-Rastogi-03/carcode/main/install.sh | bash`
  checks your Mac, offers to install missing tools, configures carcode, starts it and builds the
  Siri Shortcut. `--yes` runs it without questions for scripts and AI agents.
- **`./carcode talk`.** Talk to carcode out loud in the terminal, without a phone or a car.
- **`./carcode doctor`.** Checks every piece of the setup and prints the fix for anything wrong;
  `--json` gives machine-readable output.
- **`./carcode setup` flags.** `--workdir`, `--name`, `--title`, `--language` and `--gh-user`
  write your settings without editing `.env`.
- **`./carcode update` and `./carcode version`.**
- **AGENTS.md.** Step-by-step instructions so Claude Code and other agents can install and operate
  carcode, and know which steps to hand back to you.
- New black-and-white README, banner, demo and flow diagram.

## 1.0.0

- First release: Siri Shortcut, Cloudflare quick tunnel, warm Claude Code sessions per device,
  half-sentence joining, confirm-before-acting prompt, live dashboard and the `./carcode` CLI.
