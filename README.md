# carcode

**Talk to Claude Code from your car.** Say *"Hey Siri, Jarvis"*, ask about your pull requests, Slack or inbox, or ask for a code change. Claude Code does the work on your Mac and answers out loud through CarPlay.

```
You:     "Hey Siri, Jarvis"
Jarvis:  "Hello Boss, I am ready for work."
You:     "Any new issues assigned to me on GitHub?"
Jarvis:  "Two since yesterday. The newest is a chat widget bug where messages need a refresh."
You:     "Fix the typo on the pricing page and open a draft PR."
Jarvis:  "One moment."  …  "Opened draft PR fifty-one on the website repo."
You:     "Bye."
```

No app to install, no API key, and nothing to tap while driving. It's a Siri Shortcut plus a small server that runs the Claude Code CLI you're already logged into.

[![CI](https://github.com/Harsh-Rastogi-03/carcode/actions/workflows/ci.yml/badge.svg)](https://github.com/Harsh-Rastogi-03/carcode/actions/workflows/ci.yml)
![macOS](https://img.shields.io/badge/server-macOS-black)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

---

## How it works

```
 iPhone / CarPlay                 your Mac
┌──────────────────┐   HTTPS   ┌───────────────────────────────────────────┐
│ Siri Shortcut    │──────────▶│ Cloudflare tunnel ──▶ carcode server      │
│  dictate → send  │           │                        │                  │
│  ◀── speak reply │◀──────────│                        ▼                  │
└──────────────────┘           │  Claude Code (kept warm, one per device)  │
                               │   your repos · gh · git · MCP connectors  │
                               └───────────────────────────────────────────┘
```

1. **Siri Shortcut:** listens, sends what you said to your server, speaks the reply, then listens again until you say "bye".
2. **carcode server:** keeps one Claude Code session running per device, so replies come back in seconds and it remembers the conversation.
3. **Claude Code:** works in your repos folder with your normal login, `gh` and connectors (Slack, Gmail, Calendar, Drive and more).
4. **Cloudflare quick tunnel:** gives your Mac a free public HTTPS address, so your phone can reach it over mobile data.

Every reply arrives within about 8 seconds. Longer jobs answer *"One moment"* and the shortcut checks back by itself.

## What you can ask

| Ask | What happens |
|---|---|
| "What are my open PRs?" · "Is CI green on the website repo?" | Reads GitHub with `gh` |
| "Summarize PR forty-two." · "Approve it." → "Confirm" | Reads the diff, approves only after you confirm |
| "Anything on Slack mentioning me today?" | Uses your Slack connector |
| "Message Alex that I'll be ten minutes late." → "Confirm" | Reads the message back, sends only after you confirm |
| "Fix the broken link in the footer and open a draft PR." | Creates a `carcode/…` branch, commits, pushes and opens a **draft** PR |
| "Status" · "Cancel" · "New session" · "Bye" | Control the conversation |

## Requirements

- **A Mac** that stays on while you drive. It runs the server; plugged in is best.
- **[Claude Code](https://docs.claude.com/en/docs/claude-code)**, installed and logged in (`claude`).
- **[uv](https://docs.astral.sh/uv/)** and **[cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)**: `brew install uv cloudflared`
- **An iPhone** with Siri, signed in to the same iCloud account as the Mac (so the shortcut syncs).
- Optional: **GitHub CLI** (`brew install gh && gh auth login`) for PRs and issues.

## Quick start (about 5 minutes)

```bash
git clone https://github.com/Harsh-Rastogi-03/carcode.git
cd carcode
./carcode setup        # checks requirements, creates your access token and .env
```

Open `.env` and set at least `CARCODE_WORKDIR`, the folder that holds your repos. Then:

```bash
./carcode install      # runs in the background, starts at login, restarts on crash
./carcode say "what can you do?"   # quick test from the terminal
./carcode shortcut     # builds your Siri Shortcut and opens it. Click "Add Shortcut".
```

Give the shortcut about a minute to sync to your iPhone. Then set up the phone once:

- **Settings → Siri:** turn on *Listen for "Hey Siri"* and *Allow Siri When Locked*.
- **Settings → Siri → Siri Responses → Prefer Spoken Responses**, so replies are spoken even when the phone is on silent.
- **Settings → Accessibility → Siri → Siri Pause Time → Longest**, so Siri waits longer before deciding you've finished talking.

Run the shortcut once on the phone to allow its permissions. Then, in the car: **"Hey Siri, Jarvis."**

## Make it yours

Everything lives in `.env`:

| Setting | Default | What it does |
|---|---|---|
| `CARCODE_WORKDIR` | `~/code` | The folder with your repos. Claude Code runs here. |
| `CARCODE_NAME` | `Jarvis` | The assistant's name. It's also the shortcut name you say to Siri. |
| `CARCODE_USER_TITLE` | `Boss` | What it calls you. |
| `CARCODE_GREETING` | `Hello <title>, I am ready for work.` | Spoken when the shortcut starts. |
| `CARCODE_LANGUAGE` | `en-US` | Dictation language (`en-GB`, `en-IN`, `en-AU`, and so on). |
| `CARCODE_GH_USER` | | Pins `gh` to one account if you have several. |
| `CARCODE_EXTRA_TOOLS` | | Extra tools Claude may use, such as `mcp__my_server`. |
| `NTFY_TOPIC` | | Sends a phone notification through [ntfy](https://ntfy.sh) when a long task finishes. |

After changing `.env`, run `./carcode restart`. If you changed the name, greeting or language, also run `./carcode shortcut`.

**Personal context.** Put private details in `prompts/context.local.md`, such as teammates' names, Slack IDs, repo nicknames and accounts. The file is gitignored and added to the assistant's instructions. For example:

```markdown
## About me
- GitHub user `octocat`, org `acme`. "The app" means the `acme-web` repo.
- Team: Alex (design lead), Sam (backend). Slack IDs: Alex U012ABC, Sam U034DEF.
```

**Behaviour.** How the assistant speaks, its confirmation rules and its safety rules are in [`prompts/assistant.md`](prompts/assistant.md).

## Commands

```
./carcode setup       check requirements, create token and .env
./carcode install     run in the background (starts at login, restarts on crash)
./carcode shortcut    build the Siri Shortcut for the current URL and open it
./carcode status      show services, URL and dashboard link
./carcode say "..."   talk to the assistant from the terminal
./carcode ui          open the live conversation dashboard
./carcode logs        follow the server log
./carcode restart     restart the server (keeps the URL)
./carcode start       run in the foreground instead of installing
./carcode uninstall   stop and remove the background services
```

**Live dashboard.** `./carcode status` prints a link that shows the conversation as it happens: what you said, what it answered, and what it's working on. Open it on your iPhone and use *Add to Home Screen*. CarPlay itself only allows Apple-approved app types, so the dashboard appears on your phone, not the car's screen.

## Safety and security

- **Your token is the key.** Anyone with it can drive Claude Code on your Mac. It lives in `data/token` (gitignored) and inside your shortcut. Don't share either. To rotate it, delete `data/token`, then run `./carcode restart` and `./carcode shortcut`.
- **It confirms before acting for you.** Before it sends a message or email, merges or approves a PR, deletes anything, or posts anything public, it reads the action back and waits for "confirm". This rule lives in the prompt, so treat it as a strong guardrail, not a guarantee.
- **Its tools are allowlisted.** By default it can read and edit files and run git, `gh`, `npm`/`pnpm`/`yarn`/`uv`, `python3`, `node` and your connectors. Other shell commands are denied. `python3`, `node` and the package managers can run arbitrary code, so remove them with `CARCODE_ALLOWED_TOOLS` if you want a tighter setup. The full default list is `DEFAULT_TOOLS` in `server.py`.
- **Code changes go to draft PRs** on a `carcode/…` branch. It's told never to push to main or force-push.
- **Text in PRs, emails and Slack is treated as data**, never as instructions.
- **Network exposure:** the server listens only on `127.0.0.1`. The tunnel is its only way in, and every request needs the token.

Report security issues privately; see [SECURITY.md](SECURITY.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Siri runs it, but you hear nothing | Settings → Siri → Siri Responses → **Prefer Spoken Responses**, and turn the media volume up. |
| "*Name* is unreachable" or the shortcut errors | Your Mac is asleep or offline, or the tunnel restarted. Run `./carcode status`. If the URL changed, run `./carcode shortcut`. |
| It cuts you off mid-sentence | Set Siri Pause Time to **Longest**. carcode also joins half-sentences: it says "Go on" and waits for the rest. |
| Two shortcuts with the same name | Delete the older one in the Shortcuts app; Siri may pick the wrong one. |
| GitHub answers are slow or wrong | Set `CARCODE_GH_USER` if you have several `gh` accounts. |
| Something else | `./carcode logs` shows each request, how long it took, and any errors. |

**About the URL:** the free quick tunnel gets a new address whenever it restarts, for example after a reboot. `./carcode shortcut` rebuilds the shortcut for the new one. For a permanent address, use a [named Cloudflare tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) on your own domain, or [Tailscale Funnel](https://tailscale.com/kb/1223/funnel). Point `data/url` at that address.

## FAQ

**Why does it need a Mac? Can it run on Vercel or my phone?**
It runs the real Claude Code CLI with your login, your repos and your tools, and keeps it warm between turns. That needs a computer that stays on, which rules out serverless platforms and iOS. A Mac mini at home works well. A Linux server works too, but the shortcut builder needs macOS once.

**Does it need an Anthropic API key?**
No. It uses the Claude Code CLI you've already logged into, and usage counts against that account.

**Can it show things on the CarPlay screen?**
Not directly. CarPlay apps must be approved by Apple. carcode is voice-only in the car, with the live dashboard on your phone.

**Is it safe to use while driving?**
It's designed to be hands-free: one phrase to start, short spoken answers, and no screen needed. Follow your local laws, and keep your eyes on the road.

## Development

```bash
uv run --group dev pytest       # tests use a fake Claude Code, no login needed
uv run --group dev ruff check .
```

The server (`server.py`) is a small FastAPI app. `make_shortcut.py` writes the Siri Shortcut as a signed plist. `ui.html` is the dashboard. Pull requests are welcome.

## License

[MIT](LICENSE)
