"""Generate the signed Siri Shortcut for your carcode server.

Usage: ./carcode shortcut        (or: python3 make_shortcut.py [--no-sign])
Writes data/<Name>.shortcut wired to the current URL and token. Open it on a Mac
to import it into Shortcuts; iCloud syncs it to your iPhone.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OBJ = "￼"  # placeholder character where a variable sits inside text


def load_env(path: Path = ROOT / ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                values[key.strip()] = value.strip().strip('"').strip("'")
    return {**values, **{k: v for k, v in os.environ.items() if k.startswith("CARCODE_")}}


def uid() -> str:
    return str(uuid.uuid4()).upper()


def text(s: str) -> dict:
    return {"Value": {"string": s, "attachmentsByRange": {}},
            "WFSerializationType": "WFTextTokenString"}


def var_text(output_uuid: str, name: str) -> dict:
    ref = {"OutputUUID": output_uuid, "Type": "ActionOutput", "OutputName": name}
    return {"Value": {"string": OBJ, "attachmentsByRange": {"{0, 1}": ref}},
            "WFSerializationType": "WFTextTokenString"}


def var(output_uuid: str, name: str) -> dict:
    ref = {"OutputUUID": output_uuid, "Type": "ActionOutput", "OutputName": name}
    return {"Value": ref, "WFSerializationType": "WFTextTokenAttachment"}


def named(name: str) -> dict:
    return {"Value": {"Type": "Variable", "VariableName": name},
            "WFSerializationType": "WFTextTokenAttachment"}


def fields(items: list[tuple[str, dict]]) -> dict:
    return {"Value": {"WFDictionaryFieldValueItems": [
        {"WFItemType": 0, "WFKey": text(k), "WFValue": v} for k, v in items
    ]}, "WFSerializationType": "WFDictionaryFieldValue"}


def action(ident: str, **params) -> dict:
    return {"WFWorkflowActionIdentifier": f"is.workflow.actions.{ident}",
            "WFWorkflowActionParameters": params}


def build_workflow(url: str, token: str, greeting: str, language: str) -> dict:
    """The shortcut: greet, then loop dictate -> POST -> speak, polling slow answers."""

    def post(out_uuid: str, body: dict) -> dict:
        return action("downloadurl", UUID=out_uuid, WFURL=url, WFHTTPMethod="POST",
                      ShowHeaders=True,
                      WFHTTPHeaders=fields([("X-Carcode-Token", text(token)),
                                            ("Content-Type", text("application/json"))]),
                      WFHTTPBodyType="JSON",
                      WFJSONValues=fields([("text", body), ("device", text("iphone"))]))

    loop, end_if, poll, poll_if = uid(), uid(), uid(), uid()
    heard, reply, said, end, pending = uid(), uid(), uid(), uid(), uid()
    poll_reply, poll_said, poll_pending = uid(), uid(), uid()

    actions = [
        action("speaktext", WFText=text(greeting)),
        action("repeat.count", GroupingIdentifier=loop, WFControlFlowMode=0, WFRepeatCount=30),
        action("dictatetext", UUID=heard, WFSpeechLanguage=language,
               WFDictateTextStopListening="After Pause"),
        post(reply, var_text(heard, "Dictated Text")),
        action("getvalueforkey", UUID=said, WFDictionaryKey="speak",
               WFInput=var(reply, "Contents of URL")),
        action("speaktext", WFText=var_text(said, "Dictionary Value")),
        # The server sets "end" when you say bye / that's all.
        action("getvalueforkey", UUID=end, WFDictionaryKey="end",
               WFInput=var(reply, "Contents of URL")),
        action("conditional", GroupingIdentifier=end_if, WFControlFlowMode=0, WFCondition=100,
               WFInput={"Type": "Variable", "Variable": var(end, "Dictionary Value")}),
        action("exit"),
        action("conditional", GroupingIdentifier=end_if, WFControlFlowMode=2),
        # Slow answers come back with "pending"; ask again until they're ready.
        action("getvalueforkey", UUID=pending, WFDictionaryKey="pending",
               WFInput=var(reply, "Contents of URL")),
        action("setvariable", WFVariableName="Pending", WFInput=var(pending, "Dictionary Value")),
        action("repeat.count", GroupingIdentifier=poll, WFControlFlowMode=0, WFRepeatCount=6),
        action("conditional", GroupingIdentifier=poll_if, WFControlFlowMode=0, WFCondition=100,
               WFInput={"Type": "Variable", "Variable": named("Pending")}),
        post(poll_reply, text("__wait__")),
        action("getvalueforkey", UUID=poll_said, WFDictionaryKey="speak",
               WFInput=var(poll_reply, "Contents of URL")),
        action("speaktext", WFText=var_text(poll_said, "Dictionary Value")),
        action("getvalueforkey", UUID=poll_pending, WFDictionaryKey="pending",
               WFInput=var(poll_reply, "Contents of URL")),
        action("setvariable", WFVariableName="Pending",
               WFInput=var(poll_pending, "Dictionary Value")),
        action("conditional", GroupingIdentifier=poll_if, WFControlFlowMode=2),
        action("repeat.count", GroupingIdentifier=poll, WFControlFlowMode=2),
        action("repeat.count", GroupingIdentifier=loop, WFControlFlowMode=2),
    ]
    return {
        "WFWorkflowActions": actions,
        "WFWorkflowClientVersion": "2605.0.5",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4282601983,
                           "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": False,
    }


def main() -> None:
    cfg = load_env()
    data = Path(cfg.get("CARCODE_DATA_DIR", ROOT / "data")).expanduser()
    try:
        url = (data / "url").read_text().strip()
        token = (data / "token").read_text().strip()
    except FileNotFoundError:
        sys.exit("No URL or token yet. Start carcode first: ./carcode install")
    name = cfg.get("CARCODE_NAME", "Jarvis")
    title = cfg.get("CARCODE_USER_TITLE", "Boss")
    greeting = cfg.get("CARCODE_GREETING", f"Hello {title}, I am ready for work.")
    language = cfg.get("CARCODE_LANGUAGE", "en-US")

    workflow = build_workflow(f"{url}/voice", token, greeting, language)
    unsigned = data / f"{name}-unsigned.shortcut"
    signed = data / f"{name}.shortcut"
    unsigned.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY))
    if "--no-sign" in sys.argv:
        print(unsigned)
        return
    result = subprocess.run(["shortcuts", "sign", "--mode", "anyone",
                             "--input", str(unsigned), "--output", str(signed)],
                            capture_output=True, text=True)
    unsigned.unlink()
    if result.returncode:
        reason = result.stderr or result.stdout
        sys.exit(f"Signing failed (needs macOS and an iCloud login): {reason}")
    print(signed)


if __name__ == "__main__":
    main()
