#!/usr/bin/env python
from typing import Callable
import requests
import json
import os
import argparse
from pathlib import Path
from dataclasses import dataclass

OUTPUT_ENABLED = False
URL_CHAT = (
    f"http://localhost:{os.environ.get('LLAMA_CPP_PORT', 10000)}/v1/chat/completions"
)


def generate(messages: list[dict], on_text: Callable[[str], None], stop: list[str]):
    request_data = {
        "messages": messages,
        "stream": True,
    }
    if stop:
        request_data["stop"] = stop

    response = requests.post(URL_CHAT, json=request_data, stream=True)
    response.raise_for_status()
    for bdata in response.iter_lines():
        data = bdata.decode().strip().removeprefix("data: ")
        if not data:
            continue
        choice = json.loads(data)["choices"][0]
        if "delta" not in choice:
            continue
        delta = choice["delta"]
        if "content" not in delta:
            break
        content = delta["content"]
        if content is None:
            continue
        on_text(content)
    on_text("")


class DefaultTemplate:
    def __init__(self, filename: str):
        self.filename = filename
        self.lines = Path(filename).read_text().splitlines()

    def stop(self):
        return ["<|rewrite-end|>"]

    def get_todo(self, instruction):
        return os.environ.get("LLAMA_TODO", f"// TODO: {instruction}")

    def __call__(self, start: int, end: int, instruction: str):
        lines = self.lines.copy()
        raw_section = "\n".join(lines[start:end])
        if raw_section.strip() == "":
            lines[start] += self.get_todo(instruction)
            raw_section = "\n".join(lines[start:end])

        section = f"<|rewrite-start|>\n{raw_section}\n<|rewrite-end|>"
        lines[start] = f"<|rewrite-start|>\n{lines[start]}"
        lines[end] = f"<|rewrite-end|>\n{lines[end]}"
        content = "\n".join(lines)
        s = "You are a helpful assistant."
        m1 = """
* You will be given a document named `{filename}` whose content will be placed between `<|document-start|>` and `<|document-end|>` tags.
* Your task is to rewrite a part of the given document according to the instruction that will be placed between `<|instruction-start|>` and `<|instruction-end|>` tags
* Part that needs to be rewritten will be marked with `<|rewrite-start|>` and `<|rewrite-end|>` tags.
* You need to examine the context of the documnt before and after parts that need to be rewritten.
* Your reply must start with acknowledgement of the task, followed by `<|rewrite-start|>`
* Your reply must end with `<|rewrite-end|>`
* Your reply must contain only the rewritten part. No additional commentary is required.
* Your rewrite should only rewrite selected section, it should not rewrite previous or the next
* That output will be copy-pasted instead of the original part.

<|document-start|>
{content}
<|document-end|>

Instruction:
<|instruction-start|>
{instruction}
<|instruction-end|>

Section to rewrite:
{section}
""".format(
            filename=self.filename,
            content=content,
            instruction=instruction,
            section=section,
        ).strip()
        m2 = "I understood I need to rewrite the text. Here is the new version\n<|rewrite-start|>\n"
        return [
            {"role": "system", "content": s},
            {"role": "user", "content": m1},
            {"role": "assistant", "content": m2},
        ]


import sys


@dataclass
class PrintWithoutEndTag:
    line: str = ""

    def __call__(self, txt: str):
        STOP = "<|rewrite-end|>"
        # There are some tokens that have \n in the middle.
        # Making sure main logic has no to deal with it,
        # it simplifies it
        if len(txt) >= 2 and "\n" in txt:
            idx = txt.find("\n")
            head, tail = txt[:idx], txt[idx + 1 :]
            if head:
                self(head)
            self("\n")
            if tail:
                self(tail)
            return

        self.line += txt

        if self.line.startswith(STOP):
            # the line was started via stop word.
            # Whatever happened later irrelevant
            return

        if STOP.startswith(self.line):
            # We don't know if it safe to print or not
            return

        # We can discard the cache as we know it's safe to print
        print(self.line, end="", flush=True)
        self.line = ""


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--prompt", type=str)
    args.add_argument("--file", type=str)
    args.add_argument(
        "--range",
        type=str,
        help="Line range in form of start..end (e.g. 4..5), start included, end not",
    )

    ns = args.parse_args()

    file = ns.file
    prompt = ns.prompt
    assert ns.range
    assert ".." in ns.range
    assert file
    assert prompt
    (start, end) = (int(x) - 1 for x in ns.range.split(".."))
    assert start < end

    lines = Path(file).read_text().splitlines()
    assert end < len(lines)

    prompter = DefaultTemplate(file)
    prompt = prompter(start, end, prompt)
    print("```")
    print(prompt[1]["content"])
    print("```\n")

    print("goes to")
    print("\n```")
    generate(prompt, PrintWithoutEndTag(), prompter.stop())
    print("```")


if __name__ == "__main__":
    main()
