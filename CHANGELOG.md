# Changelog

## 1.1.0

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
