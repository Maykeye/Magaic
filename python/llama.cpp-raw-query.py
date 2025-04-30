#!/usr/bin/env python
import requests
import json
import sys
import sqlite3
import os

use_prompt = True
use_think = True
LOGGING_PATH_ENV = "OLLAMA_QUERY_LOGGING_PATH"


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


def convert_prompt(query: str):
    if not use_prompt:
        return query

    def apply_role(role):
        nonlocal lines
        nonlocal line
        nonlocal i
        line = line[line.find(">") + 1 :]
        line = line.removeprefix(":")
        line = line.removeprefix(" ")
        line = f"<|im_start|>{role}\n{line}"
        lines[i] = line
        if i:
            lines[i - 1] += "<|im_end|>"
        return role

    lines = query.splitlines()
    first_line = lines[0].lower()
    if not first_line.startswith("<sys>"):
        if not first_line.startswith("<usr>") and not first_line.startswith("<ai>"):
            lines[0] = "<usr>: " + lines[0]
        lines = ["<sys>: You are a helpful assistant"] + lines

    last_role = None
    for i, line in enumerate(lines):
        line = line.rstrip()
        if line.lower().startswith("<sys>"):
            last_role = apply_role("system")
        if line.lower().startswith("<usr>"):
            last_role = apply_role("user")
        if line.lower().startswith("<ai>"):
            last_role = apply_role("assistant")
        lines[i] = line

    if not use_think:
        lines.append("\\no_think")

    if last_role != "assistant":
        i, line = len(lines), ""
        lines.append(line)
        last_role = apply_role("assistant")
    raw = "\n".join(lines)
    return raw


if len(sys.argv) > 1:
    if sys.argv[1] == "--raw":
        del sys.argv[1]
        use_prompt = False

if sys.argv[1] == "--no-think":
    del sys.argv[1]
    use_think = False

if len(sys.argv) > 1:
    if sys.argv[1] == "--file":
        assert len(sys.argv) == 3
        raw_prompt = open(sys.argv[2]).read()
    else:
        raw_prompt = sys.argv[1]
else:
    raw_prompt = "<sys>:You are helpful assistant, your theme is touhou lore.\n<USR>who is Marisa"

prompt = convert_prompt(raw_prompt)

data = {"prompt": prompt, "stream": True}

response = requests.get("http://localhost:10000/props")
props = response.content.decode()
props_dict = json.loads(props)
model_id = props_dict["model_path"]


total_response = ""
error_message = None
can_print = use_think
try:
    response = requests.post(
        "http://localhost:10000/completion", json=data, stream=True
    )
    response.raise_for_status()
    for data in response.iter_lines(decode_unicode=True):
        data = data.strip().removeprefix("data: ")
        if not data:
            continue
        content = json.loads(data)["content"]
        total_response += content
        if can_print:
            print(content, flush=True, end="")
        elif total_response.endswith("\n</think>\n\n"):
            total_response = ""
            can_print = True
    print()
except KeyboardInterrupt:
    total_response += "(abort)"
    print("(abort)")
    error_message = "KeyboardInterrupt"
except Exception as e:
    error_message = f"{e}"
    raise (e)

mode = "chat" if use_prompt else "raw"
log(model_id, mode, prompt, total_response, error_message)
