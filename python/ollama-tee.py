#!/usr/bin/python
import json
import requests
import os
import sys
import sqlite3
from pathlib import Path

LOGGING_PATH_ENV = "OLLAMA_QUERY_LOGGING_PATH"
file_dst = None


def create_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS log(model TEXT NOT NULL, mode TEXT NOT NULL, request TEXT NOT NULL, response NULL, error NULL DEFAULT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )


def log(model, mode, request, response, error):
    path = os.environ.get(LOGGING_PATH_ENV)
    if not path:
        return
    try:
        conn = sqlite3.connect(path)
        create_table(conn)
        with conn as cur:
            cur.execute(
                "INSERT INTO log(model, mode, request, response, error) VALUES(?,?,?,?,?)",
                (model, mode, request, response, error),
            )
    except Exception as e:
        print(f"Logging error: {e}", file=sys.stderr)


def query_log(query):
    path = os.environ.get(LOGGING_PATH_ENV)
    if not path:
        raise Exception(f"No {LOGGING_PATH_ENV}")
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        create_table(conn)
        with conn as cur:
            data = cur.execute(query).fetchall()
            data = [dict(row) for row in data]
            print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Logging error: {e}", file=sys.stderr)


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
        "<usr>": "user",
        "<user>": "user",
        "<ai>": "assistant",
        "<sys>": "system",
        "<system>": "system",
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

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"num_ctx": 8192},
    }

    response = requests.post(url, json=payload, stream=True)
    try:
        for data in response.iter_lines():
            if not data:
                continue
            as_dict = json.loads(data.decode())
            token = as_dict["message"]["content"]
            print(token, end="", flush=True)
            if file_dst:
                file_dst.write(token)
                # pressing Ctrl-C from nvim doesn't send us to KeyboardInterrupt
                file_dst.flush()
    except KeyboardInterrupt:
        print("INTERRUPTED")
    finally:
        if file_dst:
            file_dst.close()


def chat_non_stream(model, messages, url, prompt):
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": 8192},
    }
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
    prompt = ""
    if sys.argv[1] == "--file":
        del sys.argv[1]
        global file_dst
        prompt = Path(sys.argv[1]).read_text()
        file_dst = open(sys.argv[1], "a")
        del sys.argv[1]

    if sys.argv[1] == "log":
        assert len(sys.argv) == 1
        return query_log(sys.argv[2])

    model = sys.argv[1]
    del sys.argv[1]

    if len(sys.argv) > 1:
        assert not sys.argv[1].startswith("--")
    prompt = prompt or sys.argv[1]
    chat(model, prompt)


if __name__ == "__main__":
    main()
