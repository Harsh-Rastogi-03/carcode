#!/usr/bin/env python3
"""Stands in for `claude -p --input-format stream-json --output-format stream-json`.

Replies "You said: <text>". Words in the message change behaviour:
"slow" waits 3 seconds, "crash" exits without answering.
"""

import json
import sys
import time
import uuid

session = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--resume"),
               str(uuid.uuid4()))

for line in sys.stdin:
    text = json.loads(line)["message"]["content"]
    if "crash" in text:
        sys.exit(1)
    if "slow" in text:
        time.sleep(3)
    thinking = {"content": [{"type": "text", "text": "..."}]}
    print(json.dumps({"type": "assistant", "message": thinking}))
    print(json.dumps({"type": "result", "result": f"You said: **{text}**", "session_id": session,
                      "num_turns": 1}), flush=True)
