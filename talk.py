"""Talk to carcode from the terminal, out loud, without a phone or a car.

Usage: ./carcode talk [--quiet] [--voice NAME]
Type what you would say to Siri. Replies are printed and spoken with macOS `say`
(use --quiet to only print). Long jobs answer "One moment" and are polled, just
like the Siri Shortcut does. Say "bye" to finish.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLL_SECONDS = 2.0


def post(base: str, token: str, text: str, device: str) -> dict:
    request = urllib.request.Request(
        f"{base}/voice",
        data=json.dumps({"text": text, "device": device}).encode(),
        headers={"Content-Type": "application/json", "X-Carcode-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        return json.loads(error.read() or b'{"speak": "The server returned an error."}')


class Speaker:
    def __init__(self, quiet: bool, voice: str | None) -> None:
        self.enabled = not quiet and shutil.which("say") is not None
        self.voice = voice

    def __call__(self, text: str) -> None:
        if self.enabled and text:
            args = ["say", *(["-v", self.voice] if self.voice else []), text]
            subprocess.run(args, check=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Talk to carcode from the terminal.")
    parser.add_argument("--quiet", action="store_true", help="print replies without speaking them")
    parser.add_argument("--voice", help="macOS voice for replies, e.g. Samantha (see: say -v ?)")
    parser.add_argument("--device", default="terminal", help="session name (default: terminal)")
    args = parser.parse_args(argv)

    port = os.environ.get("PORT", "8787")
    base = os.environ.get("CARCODE_URL", f"http://127.0.0.1:{port}")
    token_file = ROOT / "data" / "token"
    if not token_file.exists():
        print("No access token yet. Run ./carcode setup first.", file=sys.stderr)
        return 1
    token = token_file.read_text().strip()

    name = os.environ.get("CARCODE_NAME", "Jarvis")
    title = os.environ.get("CARCODE_USER_TITLE", "Boss")
    greeting = os.environ.get("CARCODE_GREETING") or f"Hello {title}, I am ready for work."
    speak = Speaker(args.quiet, args.voice)

    print(f"Talking to {name}. Type what you'd say in the car; 'bye' to finish.\n")
    print(f"{name:>8}  {greeting}")
    speak(greeting)

    while True:
        try:
            heard = input(f"{'You':>8}  ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not heard:
            continue
        try:
            reply = post(base, token, heard, args.device)
        except urllib.error.URLError:
            print(f"{name:>8}  (carcode isn't answering on {base}. Run ./carcode status.)")
            return 1
        while True:
            text = reply.get("speak", "")
            print(f"{name:>8}  {text}")
            speak(text)
            if reply.get("pending") != "yes":
                break
            time.sleep(POLL_SECONDS)
            reply = post(base, token, "__wait__", args.device)
        if reply.get("end") == "yes":
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
