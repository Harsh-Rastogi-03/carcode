import plistlib

import make_shortcut


def test_workflow_is_a_valid_shortcut():
    wf = make_shortcut.build_workflow("https://example.com/voice", "tok", "Hello Boss.", "en-GB")
    plistlib.loads(plistlib.dumps(wf, fmt=plistlib.FMT_BINARY))
    ids = [a["WFWorkflowActionIdentifier"].split(".")[-1] for a in wf["WFWorkflowActions"]]
    assert ids[0] == "speaktext"
    assert ids.count("downloadurl") == 2  # the main request and the poll
    assert ids[-1] == "count"  # the loop closes


def test_workflow_carries_url_token_and_language():
    wf = make_shortcut.build_workflow("https://example.com/voice", "tok", "Hi.", "en-IN")
    posts = [a["WFWorkflowActionParameters"] for a in wf["WFWorkflowActions"]
             if a["WFWorkflowActionIdentifier"].endswith("downloadurl")]
    assert all(p["WFURL"] == "https://example.com/voice" for p in posts)
    header = posts[0]["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"][0]
    assert header["WFKey"]["Value"]["string"] == "X-Carcode-Token"
    assert header["WFValue"]["Value"]["string"] == "tok"
    dictate = next(a for a in wf["WFWorkflowActions"]
                   if a["WFWorkflowActionIdentifier"].endswith("dictatetext"))
    assert dictate["WFWorkflowActionParameters"]["WFSpeechLanguage"] == "en-IN"


def test_load_env_reads_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CARCODE_NAME", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nCARCODE_NAME=Friday\nCARCODE_LANGUAGE='en-AU'\n")
    cfg = make_shortcut.load_env(env)
    assert cfg["CARCODE_NAME"] == "Friday"
    assert cfg["CARCODE_LANGUAGE"] == "en-AU"
