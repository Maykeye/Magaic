#!/usr/bin/env python
from typing import Optional, TextIO
import requests
import json
import sys
import sqlite3
import os
from dataclasses import dataclass


@dataclass
class Context:
    port: int = 10000
    logging_path_env: str = "LLM_QUERY_LOGGING_PATH"
    logging_path: str = ""
    input_prompt: str = ""

    use_prompt: bool = True
    use_think: bool = True
    use_tee: bool = False
    filename: Optional[str] = None
    file_dst: Optional[TextIO] = None
    n_predict: int = 0

    def __post_init__(self):
        if path := os.environ.get(self.logging_path_env):
            self.logging_path = path
        else:
            print(
                f"*** LOGGING DISABLED due to envvar {self.logging_path_env}",
                file=sys.stderr,
            )

    def close_dst_file(self):
        if self.file_dst:
            self.file_dst.close()

    def url(self, tail: str) -> str:
        tail = tail.removeprefix("/")
        return f"http://localhost:{self.port}/{tail}"


def create_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS log(model TEXT NOT NULL, mode TEXT NOT NULL, request TEXT NOT NULL, response NULL, error NULL DEFAULT NULL, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )


def log(ctx: Context, model, request, response, error):
    mode = "chat" if ctx.use_prompt else "raw"
    if not ctx.logging_path:
        return
    try:
        conn = sqlite3.connect(ctx.logging_path)
        create_table(conn)
        with conn as cur:
            cur.execute(
                "INSERT INTO log(model, mode, request, response, error) VALUES(?,?,?,?,?)",
                (model, mode, request, response, error),
            )
        conn.close()
    except Exception as e:
        print(f"Logging error: {e}", file=sys.stderr)


def convert_prompt(ctx: Context):
    if not ctx.use_prompt:
        return ctx.input_prompt

    def apply_role(role):
        new_line = line[line.find(">") + 1 :]
        new_line = new_line.removeprefix(":")
        new_line = new_line.removeprefix(" ")
        new_line = f"<|im_start|>{role}\n{new_line}"
        lines[i] = new_line
        if i:
            lines[i - 1] += "<|im_end|>"
        return role

    lines = ctx.input_prompt.splitlines()
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

    if not ctx.use_think:
        lines.append("\\no_think")

    if last_role != "assistant":
        i, line = len(lines), ""
        lines.append(line)
        last_role = apply_role("assistant")
    raw = "\n".join(lines)
    return raw


def parse_args() -> Context:
    ctx = Context()
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--raw", "--tee"):
            ctx.use_tee = sys.argv[1] == "--tee"
            ctx.use_prompt = False
            del sys.argv[1]

    if sys.argv[1] == "--no-think":
        del sys.argv[1]
        ctx.use_think = False

    if len(sys.argv) > 1:
        if sys.argv[1] == "--file":
            assert len(sys.argv) == 3
            ctx.filename = sys.argv[2]
            ctx.input_prompt = open(ctx.filename).read()
        else:
            ctx.input_prompt = sys.argv[1]
    else:
        ctx.input_prompt = "<sys>:You are helpful assistant, your theme is touhou lore.\n<USR>who is Marisa"
    if ctx.use_tee:
        assert ctx.filename, "Filename required for a tee mode"
        ctx.file_dst = open(ctx.filename, "a")
    return ctx


def main():
    ctx = parse_args()
    prompt = convert_prompt(ctx)
    request_data = {
        "prompt": prompt,
        "stream": True,
        "params": {"n_predict": ctx.n_predict},
    }

    response = requests.get(ctx.url("/props"))
    props = response.content.decode()
    props_dict = json.loads(props)
    model_id = props_dict["model_path"]
    print(prompt)
    log(ctx, model_id, json.dumps(request_data), "<init>", None)

    total_response = ""
    error_message = None
    received = 0
    try:
        response = requests.post(ctx.url("/completion"), json=request_data, stream=True)
        response.raise_for_status()
        for bdata in response.iter_lines():
            # iter_lines(decode_unicode=True incorrectly assumes encodeding)
            data = bdata.decode().strip().removeprefix("data: ")
            if not data:
                continue
            content = json.loads(data)["content"]
            total_response += content
            print(content, flush=True, end="")
            if ctx.file_dst:
                ctx.file_dst.write(content)
                ctx.file_dst.flush()
            received += 1
            if ctx.n_predict and received >= ctx.n_predict:
                response.close()
                break
    except KeyboardInterrupt:
        total_response += "(abort)"
        if ctx.file_dst:
            ctx.file_dst.write("(abort)")
        print("(abort)")
        error_message = "KeyboardInterrupt"
    except Exception as e:
        error_message = f"{e}"
        raise e
    finally:
        ctx.close_dst_file()

    request_data["input_prompt"] = ctx.input_prompt
    log(ctx, model_id, json.dumps(request_data), total_response, error_message)


if __name__ == "__main__":
    main()

