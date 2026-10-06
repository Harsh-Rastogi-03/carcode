import talk


def run_talk(monkeypatch, tmp_path, typed, replies):
    """Run talk.main with scripted input and server replies; return what was sent."""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "token").write_text("t0k\n")
    monkeypatch.setattr(talk, "ROOT", tmp_path)
    monkeypatch.setattr(talk, "POLL_SECONDS", 0)

    inputs = iter(typed)

    def fake_input(_prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError from None

    sent = []
    queue = iter(replies)

    def fake_post(base, token, text, device):
        sent.append((token, text, device))
        return next(queue)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(talk, "post", fake_post)
    code = talk.main(["--quiet"])
    return code, sent


def test_polls_until_a_long_job_finishes(monkeypatch, tmp_path, capsys):
    code, sent = run_talk(
        monkeypatch, tmp_path,
        typed=["fix the footer"],
        replies=[
            {"speak": "One moment.", "pending": "yes"},
            {"speak": "Still working.", "pending": "yes"},
            {"speak": "Opened draft PR fifty-one."},
        ],
    )
    assert code == 0
    assert [text for _, text, _ in sent] == ["fix the footer", "__wait__", "__wait__"]
    assert all(token == "t0k" for token, _, _ in sent)
    assert "Opened draft PR fifty-one." in capsys.readouterr().out


def test_goodbye_ends_the_conversation(monkeypatch, tmp_path):
    code, sent = run_talk(
        monkeypatch, tmp_path,
        typed=["bye", "this is never sent"],
        replies=[{"speak": "Bye.", "end": "yes"}],
    )
    assert code == 0
    assert [text for _, text, _ in sent] == ["bye"]


def test_needs_a_token(monkeypatch, tmp_path):
    monkeypatch.setattr(talk, "ROOT", tmp_path)
    assert talk.main(["--quiet"]) == 1
