#!/usr/bin/env python
import requests
import json
import sys
import sqlite3
import os
import random

PORT = 10000
use_prompt = True
use_think = True
use_tee = False
LOGGING_PATH_ENV = "OLLAMA_QUERY_LOGGING_PATH"
filename = None
file_dst = None


def create_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS log(model TEXT NOT NULL, mode TEXT NOT NULL, request TEXT NOT NULL, response NULL, error NULL DEFAULT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )


def log(model, mode, request, response, error):
    path = os.environ.get(LOGGING_PATH_ENV)
    if not path:
        print(f"*** LOGGING DISABLED: {LOGGING_PATH_ENV}")
        return
    try:
        conn = sqlite3.connect(path)
        create_table(conn)
        with conn as cur:
            cur.execute(
                "INSERT INTO log(model, mode, request, response, error) VALUES(?,?,?,?,?)",
                (model, mode, request, response, error),
            )
        conn.close()
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
    if sys.argv[1] in ("--raw", "--tee"):
        use_tee = sys.argv[1] == "--tee"
        use_prompt = False
        del sys.argv[1]

if sys.argv[1] == "--no-think":
    del sys.argv[1]
    use_think = False

if len(sys.argv) > 1:
    if sys.argv[1] == "--file":
        assert len(sys.argv) == 3
        filename = sys.argv[2]
        raw_prompt = open(filename).read()
    else:
        raw_prompt = sys.argv[1]
else:
    raw_prompt = "<sys>:You are helpful assistant, your theme is touhou lore.\n<USR>who is Marisa"

if use_tee:
    assert filename, "Filename required for a tee mode"
    file_dst = open(filename, "a")

prompt = convert_prompt(raw_prompt)
N_PREDICT = 0
request_data = {"prompt": prompt, "stream": True, "params": {"n_predict": N_PREDICT}}

response = requests.get(f"http://localhost:{PORT}/props")
props = response.content.decode()
props_dict = json.loads(props)
model_id = props_dict["model_path"]
print(prompt)

total_response = ""
error_message = None
always_print = True
can_print = use_think
current_line = ""
received = 0
line_mode = True
try:
    response = requests.post(
        f"http://localhost:{PORT}/completion", json=request_data, stream=True
    )
    response.raise_for_status()
    for bdata in response.iter_lines():
        # iter_lines(decode_unicode=True incorrectly assumes encodeding)
        data = bdata.decode()
        data = data.strip().removeprefix("data: ")
        if not data:
            continue
        content = json.loads(data)["content"]
        total_response += content
        print(content, flush=True, end="")
        if file_dst:
            file_dst.write(content)
            file_dst.flush()
        received += 1
        if N_PREDICT > 0 and received >= N_PREDICT:
            response.close()
            break
    print(current_line)
except KeyboardInterrupt:
    total_response += "(abort)"
    print("(abort)")
    error_message = "KeyboardInterrupt"
except Exception as e:
    error_message = f"{e}"
    raise (e)
finally:
    if file_dst:
        file_dst.close()

mode = "chat" if use_prompt else "raw"
request_data["raw_prompt"] = raw_prompt
log(model_id, mode, json.dumps(request_data), total_response, error_message)
