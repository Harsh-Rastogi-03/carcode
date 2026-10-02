# /// script
# requires-python = ">=3.12"
# dependencies = ["fastapi>=0.115,<1", "uvicorn>=0.32,<1", "httpx>=0.27,<1"]
# ///
"""carcode server: talk to Claude Code hands-free from CarPlay via a Siri Shortcut.

POST /voice {"text": "...", "device": "iphone"} with header X-Carcode-Token.
Each device gets one long-lived Claude Code process (stream-json in and out),
so turns skip CLI startup; if it dies it is restarted with --resume.
Every reply returns within CARCODE_WAIT_SECONDS. Slower work answers
"One moment" with pending=yes, and the shortcut polls with "__wait__".
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import os
import re
import signal
import subprocess
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse


def env(name: str, default: str = "") -> str:
    # JARVIS_* is accepted for installs made before the carcode rename.
    return os.environ.get(f"CARCODE_{name}", os.environ.get(f"JARVIS_{name}", default))


ROOT = Path(__file__).resolve().parent
DATA = Path(env("DATA_DIR", str(ROOT / "data"))).expanduser()
TOKEN = env("TOKEN")
NAME = env("NAME", "Jarvis")
TITLE = env("USER_TITLE", "Boss")
WORKDIR = Path(env("WORKDIR", str(Path.home()))).expanduser()
WAIT_SECONDS = float(env("WAIT_SECONDS", "8"))
JOB_TIMEOUT = float(env("JOB_TIMEOUT", "900"))
GH_USER = env("GH_USER")  # pin gh to one account so account switches elsewhere don't matter
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

STATE_FILE = DATA / "sessions.json"
LOG_DIR = DATA / "logs"
PROMPT_FILE = ROOT / "prompts" / "assistant.md"
CONTEXT_FILE = ROOT / "prompts" / "context.local.md"  # private, gitignored
UI_FILE = ROOT / "ui.html"
MAX_LINE = 32 * 1024 * 1024  # stream-json lines can carry big tool outputs

# Tools Claude may use without asking. A bare MCP server name allows all its tools.
DEFAULT_TOOLS = ",".join([
    "Read", "Edit", "Write", "Glob", "Grep", "ToolSearch", "WebSearch", "WebFetch",
    "Bash(git *)", "Bash(gh *)", "Bash(ls *)", "Bash(cat *)", "Bash(npm *)",
    "Bash(pnpm *)", "Bash(yarn *)", "Bash(uv *)", "Bash(python3 *)", "Bash(node *)",
    "mcp__claude_ai_Slack", "mcp__claude_ai_Gmail", "mcp__claude_ai_Google_Calendar",
    "mcp__claude_ai_Google_Drive", "mcp__claude_ai_Figma", "mcp__claude_ai_Claude_Docs",
])
ALLOWED_TOOLS = ",".join(filter(None, [env("ALLOWED_TOOLS", DEFAULT_TOOLS), env("EXTRA_TOOLS")]))

RESET_WORDS = {"new session", "start over", "reset", "fresh start"}
CANCEL_WORDS = {"cancel", "stop", "cancel that", "stop that"}
STATUS_WORDS = {"status", "what's the status", "whats the status", "are you done",
                "is it done", "any update", "update"}
_name = re.escape(NAME.lower())
END_PATTERN = re.compile(
    r"^(ok(ay)? |thanks? (you )?|thank you )?"
    r"(bye( bye)?|by|goodbye|good bye|that'?s all|that is all|i'?m done|we'?re done|done|"
    rf"stop {_name}|exit|end( session)?)( {_name})?( thanks?( you)?)?$"
)

# Dictation stops at the first pause, so half sentences arrive on their own.
# If an utterance looks unfinished, reply "Go on" and join it with the next one.
DANGLING_WORDS = set("""
with to the a an and or of for about my on in at from that if but so is are was were
can could would will should what how when where which who whose please your our their
this these those into by than then also like as do does did plus because
""".split())
DANGLING_ENDINGS = ("tell me", "show me", "give me", "send me", "can you", "could you",
                    "would you", "will you", "i want", "i need", "let me")
STARTER_WORDS = {"can", "could", "would", "will", "what", "how", "when", "where", "which",
                 "who", "please", "tell", "show", "is", "are", "do", "does", "hey", "so"}
FRAGMENT_TTL = 45.0
MAX_FRAGMENTS = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("carcode")


class Device:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self.proc: asyncio.subprocess.Process | None = None
        self.job: asyncio.Task[str] | None = None
        self.job_text = ""
        self.unread: list[str] = []
        self.fragments: list[str] = []
        self.fragment_at = 0.0
        self.lock = asyncio.Lock()


devices: dict[str, Device] = {}
HISTORY: deque[dict] = deque(maxlen=300)


# ---------- text helpers ----------

def looks_unfinished(text: str) -> bool:
    words = re.findall(r"[a-z']+", text.lower())
    if not words or (text.rstrip().endswith(("?", ".", "!")) and len(words) > 3):
        return False
    if words[-1] in DANGLING_WORDS or " ".join(words[-3:]).endswith(DANGLING_ENDINGS):
        return True
    return len(words) <= 2 and words[0] in STARTER_WORDS


def is_goodbye(lowered: str) -> bool:
    return bool(END_PATTERN.match(re.sub(r"[^a-z' ]", "", lowered).strip()))


def to_speech(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\b[0-9a-f]{7,40}\b", "", text)
    text = re.sub(r"#(\d+)", r"\1", text)
    text = re.sub(r"[*_`>#|]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:600] or "Done."


def system_prompt() -> str:
    text = PROMPT_FILE.read_text().replace("{{name}}", NAME).replace("{{title}}", TITLE)
    if CONTEXT_FILE.exists():
        text += "\n\n" + CONTEXT_FILE.read_text()
    return text


# ---------- state ----------

def load_state() -> None:
    if STATE_FILE.exists():
        for name, sid in json.loads(STATE_FILE.read_text()).items():
            devices[name] = Device(sid)


def save_state() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({k: d.session_id for k, d in devices.items()}))


def record(device: str, heard: str, reply: dict, seconds: float) -> None:
    """Keep recent turns in memory for the live dashboard."""
    HISTORY.append({
        "ts": time.time(), "device": device,
        "heard": "" if heard == "__wait__" else heard,
        "speak": reply.get("speak", ""), "pending": bool(reply.get("pending")),
        "end": bool(reply.get("end")), "seconds": round(seconds, 1),
    })


# ---------- Claude Code process ----------

def claude_env() -> dict[str, str]:
    environ = dict(os.environ)
    if GH_USER:
        token = subprocess.run(["gh", "auth", "token", "-u", GH_USER],
                               capture_output=True, text=True).stdout.strip()
        if token:
            environ["GH_TOKEN"] = token
        else:
            log.warning("no gh token for %s; using gh's active account", GH_USER)
    return environ


def kill_proc(device: Device) -> None:
    proc, device.proc = device.proc, None
    if proc and proc.returncode is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)


async def start_proc(device: Device, name: str) -> asyncio.subprocess.Process:
    """Start (or reuse) this device's long-lived Claude Code process."""
    if device.proc and device.proc.returncode is None:
        return device.proc
    cmd = [
        CLAUDE_BIN, "-p", "--verbose",
        "--input-format", "stream-json", "--output-format", "stream-json",
        "--append-system-prompt", system_prompt(),
        "--allowedTools", ALLOWED_TOOLS,
        "--permission-mode", "acceptEdits",
    ]
    if device.session_id:
        cmd += ["--resume", device.session_id]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"claude-{name}.log", "ab") as stderr:
        device.proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=WORKDIR, env=claude_env(), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=stderr,
            start_new_session=True, limit=MAX_LINE,
        )
    log.info("[%s] started claude pid=%s resume=%s", name, device.proc.pid, device.session_id)
    return device.proc


async def read_result(proc: asyncio.subprocess.Process) -> dict:
    """Read stream-json events until this turn's result event."""
    assert proc.stdout
    while True:
        line = await proc.stdout.readline()
        if not line:
            raise RuntimeError("claude process exited")
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            return event


async def run_claude(device: Device, text: str, name: str) -> str:
    started = time.monotonic()
    message = json.dumps({"type": "user", "message": {"role": "user", "content": text}})
    for attempt in range(2):
        proc = await start_proc(device, name)
        assert proc.stdin
        try:
            proc.stdin.write((message + "\n").encode())
            await proc.stdin.drain()
            data = await asyncio.wait_for(read_result(proc), JOB_TIMEOUT)
            break
        except (TimeoutError, asyncio.CancelledError):
            kill_proc(device)  # the next turn restarts it with --resume
            raise
        except (RuntimeError, BrokenPipeError, ConnectionResetError):
            log.warning("[%s] claude process died, restarting", name)
            kill_proc(device)
            if attempt:
                return "Claude Code stopped unexpectedly. Check the server logs."
    log.info("[%s] turn done in %.1fs (turns=%s)", name, time.monotonic() - started,
             data.get("num_turns"))
    if data.get("session_id"):
        device.session_id = data["session_id"]
        save_state()
    if data.get("permission_denials"):
        log.info("[%s] denied: %s", name, data["permission_denials"])
    return to_speech(data.get("result") or "I didn't get an answer.")


async def notify(message: str) -> None:
    if not NTFY_TOPIC:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"https://ntfy.sh/{NTFY_TOPIC}", content=message.encode(),
                              headers={"Title": NAME})
    except httpx.HTTPError as exc:
        log.warning("ntfy failed: %s", exc)


async def finish_in_background(device: Device) -> None:
    assert device.job
    try:
        result = await device.job
    except asyncio.CancelledError:
        device.job = None
        return
    except TimeoutError:
        result = "That task ran too long and I stopped it."
    except Exception as exc:  # noqa: BLE001 - always report something speakable
        log.exception("job failed")
        result = f"That task failed: {type(exc).__name__}."
    device.unread.append(result)
    device.job = None
    await notify(result)


# ---------- HTTP ----------

@asynccontextmanager
async def lifespan(_: FastAPI):
    load_state()
    for name, device in devices.items():  # warm up so the first turn in the car is fast
        await start_proc(device, name)
    yield
    for device in devices.values():
        kill_proc(device)


app = FastAPI(title="carcode", lifespan=lifespan)


def speak(text: str, **extra: str) -> JSONResponse:
    return JSONResponse({"speak": text, **extra})


def request_token(request: Request) -> str:
    # X-Jarvis-Token is accepted for shortcuts made before the carcode rename.
    return request.headers.get("x-carcode-token") or request.headers.get("x-jarvis-token", "")


def authorized(request: Request) -> bool:
    return bool(TOKEN) and hmac.compare_digest(request_token(request), TOKEN)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ui", response_class=HTMLResponse)
async def ui() -> str:
    return UI_FILE.read_text().replace("{{name}}", NAME)


@app.get("/api/history")
async def history(request: Request) -> JSONResponse:
    if not authorized(request):
        return JSONResponse({"error": "bad token"}, status_code=401)
    working = [{"device": n, "task": d.job_text} for n, d in devices.items()
               if d.job and not d.job.done()]
    return JSONResponse({"name": NAME, "turns": list(HISTORY), "working": working})


@app.post("/voice")
async def voice(request: Request) -> JSONResponse:
    if not authorized(request):
        return JSONResponse({"speak": f"{NAME} rejected the token."}, status_code=401)
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return speak("I couldn't read that request.")
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(body.get("text", ""))).strip()[:1000]
    name = str(body.get("device", "iphone"))[:40]
    started = time.monotonic()
    response = await handle(text, name)
    record(name, text, json.loads(bytes(response.body)), time.monotonic() - started)
    return response


async def wait_for_result(device: Device) -> JSONResponse:
    """Hold a "__wait__" poll for a background job, returning before Siri gives up."""
    deadline = time.monotonic() + max(WAIT_SECONDS - 2, 1)
    while time.monotonic() < deadline:
        if device.unread:
            text = " ".join(device.unread)
            device.unread.clear()
            return speak(text)
        if not device.job:
            return speak("Done.")
        await asyncio.sleep(0.25)
    return speak("Still working.", pending="yes")


async def handle(text: str, name: str) -> JSONResponse:
    device = devices.setdefault(name, Device())
    lowered = text.lower().strip(" .!?")
    log.info("[%s] heard: %s", name, text)

    if not text:
        return speak("I didn't catch that.")
    if lowered == "__wait__":
        return await wait_for_result(device)
    if is_goodbye(lowered):
        return speak("Bye.", end="yes")

    async with device.lock:
        backlog = " ".join(f"Earlier task: {r}" for r in device.unread)
        device.unread.clear()

        if lowered in RESET_WORDS:
            if device.job:
                device.job.cancel()
            kill_proc(device)
            device.session_id = None
            save_state()
            return speak("Fresh session started.")

        if device.job and not device.job.done():
            if lowered in CANCEL_WORDS:
                device.job.cancel()
                return speak("Cancelled.")
            return speak(f"{backlog} Still working on: {device.job_text[:80]}.".strip())

        if lowered in STATUS_WORDS:
            return speak(backlog or "Nothing running. What next?")

        if device.fragments and time.monotonic() - device.fragment_at > FRAGMENT_TTL:
            device.fragments.clear()
        if looks_unfinished(text) and len(device.fragments) < MAX_FRAGMENTS:
            device.fragments.append(text)
            device.fragment_at = time.monotonic()
            return speak(f"{backlog} Go on.".strip())
        if device.fragments:
            text = " ".join([*device.fragments, text])
            device.fragments.clear()
            log.info("[%s] joined: %s", name, text)

        device.job_text = text
        device.job = asyncio.create_task(run_claude(device, text, name))
        done, _ = await asyncio.wait({device.job}, timeout=WAIT_SECONDS)
        if done:
            job, device.job = device.job, None
            try:
                answer = job.result()
            except Exception:  # noqa: BLE001 - never return a 500 to Siri
                log.exception("claude failed")
                answer = "Claude Code hit an error. Try again."
            return speak(f"{backlog} {answer}".strip())

        asyncio.create_task(finish_in_background(device))
        return speak(f"{backlog} One moment.".strip(), pending="yes")


if __name__ == "__main__":
    import uvicorn

    if not TOKEN:
        raise SystemExit("CARCODE_TOKEN is not set. Run ./carcode setup first.")
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8787")))
