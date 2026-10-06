#!/usr/bin/env bash
# carcode installer: talk to Claude Code from your car.
#
#   curl -fsSL https://raw.githubusercontent.com/Harsh-Rastogi-03/carcode/main/install.sh | bash
#
# Options (pass after `bash -s --` when piping):
#   --dir DIR        where to install carcode            (default: ~/carcode)
#   --workdir DIR    folder that holds your git repos     (default: asks, or ~/code)
#   --name NAME      what you'll call it: "Hey Siri, NAME" (default: Jarvis)
#   --title TITLE    how it addresses you                 (default: Boss)
#   --yes            don't ask; install missing Homebrew tools automatically
#   --no-shortcut    skip building the Siri Shortcut
#
# Example for scripts and AI agents:
#   curl -fsSL https://raw.githubusercontent.com/Harsh-Rastogi-03/carcode/main/install.sh \
#     | bash -s -- --yes --workdir ~/code
set -euo pipefail

REPO="https://github.com/Harsh-Rastogi-03/carcode.git"
DIR="$HOME/carcode"
WORKDIR=""
NAME=""
TITLE=""
YES=0
SHORTCUT=1

while (( $# )); do
  case "$1" in
    --dir)         DIR="$2"; shift 2 ;;
    --workdir)     WORKDIR="$2"; shift 2 ;;
    --name)        NAME="$2"; shift 2 ;;
    --title)       TITLE="$2"; shift 2 ;;
    --yes|-y)      YES=1; shift ;;
    --no-shortcut) SHORTCUT=0; shift ;;
    -h|--help)     sed -n '2,19p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die()  { printf '\n\033[31m%s\033[0m\n' "$*" >&2; exit 1; }

# Read answers from the terminal even when this script is piped from curl.
ask() {  # ask <prompt> <default>
  local reply=""
  if (( YES )) || [[ ! -r /dev/tty ]]; then echo "$2"; return; fi
  read -r -p "$1 [$2]: " reply < /dev/tty || true
  echo "${reply:-$2}"
}
confirm() {  # confirm <prompt>
  (( YES )) && return 0
  [[ -r /dev/tty ]] || return 1
  local reply=""
  read -r -p "$1 [Y/n]: " reply < /dev/tty || true
  [[ -z "$reply" || "$reply" =~ ^[Yy] ]]
}

bold "carcode installer: Claude Code in your car"

step "1/5  Checking your Mac"
[[ "$(uname)" == Darwin ]] || die "carcode needs a Mac: the Siri Shortcut is signed and the services run with launchd."
ok "macOS $(sw_vers -productVersion)"
command -v git >/dev/null || die "git is missing. Run: xcode-select --install"
ok "git"

missing=()
for tool in uv cloudflared; do
  if command -v "$tool" >/dev/null; then ok "$tool"; else missing+=("$tool"); fi
done
if (( ${#missing[@]} )); then
  command -v brew >/dev/null || die "Missing: ${missing[*]}. Install Homebrew from https://brew.sh, then run this again."
  if confirm "Install ${missing[*]} with Homebrew?"; then
    brew install "${missing[@]}"
  else
    die "carcode needs ${missing[*]}. Run: brew install ${missing[*]}"
  fi
fi

if command -v claude >/dev/null; then
  ok "claude (Claude Code)"
else
  die "Claude Code isn't installed. Run:
  curl -fsSL https://claude.ai/install.sh | bash
then open a new terminal, run: claude  (log in once), and run this installer again."
fi
command -v gh >/dev/null && ok "gh (GitHub CLI)" || echo "  - gh not found (optional, for GitHub questions): brew install gh && gh auth login"

step "2/5  Getting carcode"
if [[ -d "$DIR/.git" ]]; then
  git -C "$DIR" pull --ff-only --quiet && ok "updated $DIR"
else
  git clone --quiet "$REPO" "$DIR" && ok "cloned into $DIR"
fi
cd "$DIR"

step "3/5  Your settings"
default_workdir="$HOME/code"
for candidate in "$HOME/code" "$HOME/dev" "$HOME/projects" "$HOME/src" "$HOME/Developer"; do
  [[ -d "$candidate" ]] && { default_workdir="$candidate"; break; }
done
WORKDIR="${WORKDIR:-$(ask "Folder that holds your git repos" "$default_workdir")}"
WORKDIR="${WORKDIR/#\~/$HOME}"
[[ -d "$WORKDIR" ]] || die "Folder not found: $WORKDIR. Pass an existing one with --workdir."
NAME="${NAME:-$(ask "What will you call it? (\"Hey Siri, …\")" "Jarvis")}"
TITLE="${TITLE:-$(ask "How should it address you?" "Boss")}"
./carcode setup --workdir "$WORKDIR" --name "$NAME" --title "$TITLE"

step "4/5  Starting carcode in the background"
./carcode install

if (( SHORTCUT )); then
  step "5/5  Building your Siri Shortcut"
  ./carcode shortcut || echo "  Couldn't build the shortcut yet. Run ./carcode shortcut once the URL is ready."
fi

bold "
Done. Two things only you can do:"
echo "  1. In the window that opened, click \"Add Shortcut\". It syncs to your iPhone in about a minute."
echo "  2. On your iPhone: Settings → Siri → turn on \"Allow Siri When Locked\" and"
echo "     Siri Responses → \"Prefer Spoken Responses\"."
echo
echo "Then say: \"Hey Siri, $NAME\""
echo
echo "Try it right now without a phone:  cd $DIR && ./carcode talk"
echo "Check the setup any time:         cd $DIR && ./carcode doctor"
