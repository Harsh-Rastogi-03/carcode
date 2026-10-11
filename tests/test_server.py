import json
import time

import pytest
from conftest import TOKEN

import server


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("headers", [{}, {"X-Carcode-Token": "wrong"}])
def test_rejects_bad_token(client, headers):
    r = client.post("/voice", json={"text": "hi"}, headers=headers)
    assert r.status_code == 401
    assert "rejected" in r.json()["speak"]


def test_accepts_pre_rename_header(client):
    r = client.post("/voice", json={"text": "hi"}, headers={"X-Jarvis-Token": TOKEN})
    assert r.status_code == 200


def test_round_trip_strips_markdown(say):
    assert say("what are my open PRs")["speak"] == "You said: what are my open PRs"


def test_session_is_saved_and_reused(say):
    say("first")
    saved = json.loads(server.STATE_FILE.read_text())
    assert saved["phone"]
    say("second")
    assert json.loads(server.STATE_FILE.read_text()) == saved


def test_devices_are_separate(say):
    say("hello", device="phone")
    say("hello", device="ipad")
    sessions = json.loads(server.STATE_FILE.read_text())
    assert sessions["phone"] != sessions["ipad"]


@pytest.mark.parametrize("text", ["Bye", "bye.", "Bye Jarvis", "ok bye", "that's all", "Goodbye"])
def test_goodbye_ends_the_shortcut(say, text):
    assert say(text) == {"speak": "Bye.", "end": "yes"}


def test_half_sentence_is_joined_with_the_next(say):
    assert say("Can you tell me")["speak"] == "Go on."
    assert say("the weather in Delhi")["speak"] == "You said: Can you tell me the weather in Delhi"


def test_unprompted_result_does_not_answer_the_next_question(say):
    assert say("start a background job")["speak"] == "You said: start a background job"
    time.sleep(0.2)
    assert say("what time is it")["speak"] == "You said: what time is it"


def test_slow_task_answers_pending_then_poll_returns_result(say):
    first = say("do a slow task")
    assert first == {"speak": "One moment.", "pending": "yes"}
    for _ in range(6):
        reply = say("__wait__")
        if "pending" not in reply:
            break
    assert reply["speak"] == "You said: do a slow task"


def test_status_and_cancel_while_working(say):
    say("another slow one")
    assert say("hello")["speak"].startswith("Still working on")
    assert say("cancel")["speak"] == "Cancelled."
    time.sleep(0.2)
    assert say("status")["speak"] == "Nothing running. What next?"


def test_reset_starts_fresh_session(say):
    say("remember the number seven")
    old = json.loads(server.STATE_FILE.read_text())["phone"]
    assert say("new session")["speak"] == "Fresh session started."
    say("hi again")
    assert json.loads(server.STATE_FILE.read_text())["phone"] != old


def test_crashed_claude_gives_spoken_error(say):
    assert "stopped unexpectedly" in say("time to crash now")["speak"]
    assert say("still there")["speak"] == "You said: still there"


def test_dashboard(client, say):
    assert "Jarvis" in client.get("/ui").text
    assert client.get("/api/history").status_code == 401
    say("hello")
    turns = client.get("/api/history", headers={"X-Carcode-Token": TOKEN}).json()["turns"]
    assert turns[-1]["heard"] == "hello"
    assert turns[-1]["speak"] == "You said: hello"


def test_dashboard_shows_joined_and_background_turns(client, say):
    say("Can you tell me")
    say("the weather")
    say("start a background job")
    time.sleep(0.2)
    say("next")
    turns = client.get("/api/history", headers={"X-Carcode-Token": TOKEN}).json()["turns"]
    assert turns[0]["kind"] == "fragment"
    assert turns[1]["joined"] == "Can you tell me the weather"
    assert turns[3] == {**turns[3], "kind": "background", "speak": "Background task finished."}
    assert turns[4]["speak"] == "You said: next"



def test_history_is_saved_with_its_session(client, say):
    say("hello")
    saved = [json.loads(line) for line in server.HISTORY_FILE.read_text().splitlines()]
    assert saved[-1]["heard"] == "hello"
    assert saved[-1]["session"] == json.loads(server.STATE_FILE.read_text())["phone"]
    server.HISTORY.clear()
    server.load_history()
    assert saved == server.HISTORY


def test_earlier_sessions_are_imported_from_transcripts(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CLAUDE_PROJECTS", tmp_path)
    folder = tmp_path / server.re.sub(r"[^A-Za-z0-9]", "-", str(server.WORKDIR))
    folder.mkdir()

    def event(kind, ts, content, **extra):
        return json.dumps({"type": kind, "timestamp": f"2026-10-02T08:00:{ts:02d}Z",
                           "message": {"content": content}, **extra})

    text = lambda t: [{"type": "text", "text": t}]  # noqa: E731
    (folder / "car.jsonl").write_text("\n".join([
        event("user", 0, "what's on my calendar", entrypoint="sdk-cli"),
        event("assistant", 3, text("Two **meetings**.")),
        event("user", 9, "<task-notification>done</task-notification>", entrypoint="sdk-cli"),
        event("assistant", 12, text("The review is done.")),
    ]))
    (folder / "desk.jsonl").write_text(event("user", 0, "refactor this", entrypoint="cli"))
    server.STATE_FILE.write_text(json.dumps({"iphone": "car"}))

    turns = server.import_transcripts()
    assert [(t["heard"], t["speak"], t["device"], t["session"]) for t in turns] == [
        ("what's on my calendar", "Two meetings.", "iphone", "car"),
        ("", "The review is done.", "iphone", "car"),
    ]
    assert turns[0]["seconds"] == 3.0
    assert turns[1]["kind"] == "background"

@pytest.mark.parametrize(("text", "expected"), [
    ("Can you connect with", True),
    ("Can you tell me", True),
    ("Check my PRs and", True),
    ("Hey", True),
    ("What are you currently", True),
    ("May I know what you", True),
    ("What is the latest", True),
    ("Check if I got", True),
    ("Check latest message from", True),
    ("Ask", True),
    ("Read", True),
    ("Slack", False),
    ("Yes confirm", False),
    ("Thank you", False),
    ("Check Slack", False),
    ("GitHub", False),
    ("How are you", False),
    ("Confirm", False),
    ("What are my open PRs?", False),
    ("Send a Slack message to Alex saying I'll be late", False),
])
def test_looks_unfinished(text, expected):
    assert server.looks_unfinished(text) is expected


@pytest.mark.parametrize(("raw", "spoken"), [
    ("Merged **#42** in `mvp`.", "Merged 42 in mvp."),
    ("See [the PR](https://github.com/a/b/pull/1) now", "See the PR now"),
    ("Commit 3f9a2c1d pushed", "Commit pushed"),
    ("```\ncode\n```Done", "Done"),
    ("", "Done."),
])
def test_to_speech(raw, spoken):
    assert server.to_speech(raw) == spoken
