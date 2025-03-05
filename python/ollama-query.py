#!/usr/bin/python
import json
import requests
import os
import sys
import sqlite3


def log(model, mode, request, response, error):
    path = os.environ.get("OLLAMA_QUERY_LOGGING_PATH")
    if not path:
        return
    try:
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS log(model TEXT NOT NULL, mode TEXT NOT NULL, request TEXT NOT NULL, response NULL, error NULL DEFAULT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        with conn as cur:
            cur.execute(
                "INSERT INTO log(model, mode, request, response, error) VALUES(?,?,?,?,?)",
                (model, mode, request, response, error),
            )
    except Exception as e:
        print(f"Logging error: {e}", file=sys.stderr)


def raw(model, prompt):
    url = "http://localhost:11434/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    # open("/tmp/last.prompt", "w").write(json.dumps(payload, indent=2))

    response = requests.post(url, json=payload)

    if response.ok:
        content = response.json()["response"]
        log(model, "raw", prompt, content, None)
        print(content)
    else:
        err_text = f"ERR {response.status_code}: {response.text}"
        print(err_text)
        log(model, "raw", prompt, None, err_text)


def chat(model, prompt: str):
    """replace <USER> with user, replace <AI> with ai, replace <SYS> with system"""
    url = "http://localhost:11434/api/chat"

    lines: list[str] = prompt.splitlines(keepends=True)
    messages = []
    roles = {
        "<USR>": "user",
        "<USER>": "user",
        "<AI>": "assistant",
        "<SYS>": "system",
        "<SYSTEM>": "system",
    }

    for line in lines:
        for prefix, role in roles.items():
            if not line.startswith(prefix):
                continue

            line = line.removeprefix(prefix)
            line = line.removeprefix(":")  # Allow some trailing garbo
            line = line.removeprefix(" ")  # Allow some trailing garbo
            messages.append({"role": role, "content": line})
            break
        else:
            # didn't find a role.
            if messages:
                messages[-1]["content"] += line
                continue
            else:  # if no role defined, assume user is talking
                messages.append({"role": "user", "content": line})

    prompt = json.dumps(messages)
    payload = {"model": model, "messages": messages, "stream": False}
    response = requests.post(url, json=payload)

    if response.ok:
        content = response.json()["message"]["content"]
        print(content)
        log(model, "chat", prompt, content, None)
    else:
        err_text = f"ERR {response.status_code}: {response.text}"
        print(err_text)
        log(model, "chat", prompt, None, err_text)


def main():
    model = sys.argv[1]
    mode = sys.argv[2]
    if mode == "raw":
        raw(model, sys.argv[3])
    elif mode == "chat":
        chat(model, sys.argv[3])
    else:
        raise ValueError("invalid query mode")


if __name__ == "__main__":
    main()
