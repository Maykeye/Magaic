#!/usr/bin/env python
from typing import Callable, Optional, TextIO
import requests
import json
import os
import argparse
from pathlib import Path


OUTPUT_ENABLED = False
URL_CHAT = (
    f"http://localhost:{os.environ.get('LLAMA_CPP_PORT', 10000)}/v1/chat/completions"
)


def generate(messages: list[dict], on_text: Callable[[str], None]):
    request_data = {
        "messages": messages,
        "stream": True,
    }

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


def default_template(filename: str, content: str, instruction: str):
    s = "You are a helpful assistant."
    m1 = """\
* You will be given a document named `{filename}` whose content will be placed between `<|document-start|>` and `<|document-end|>` tags.
* Your task is to rewrite a part of the given document according to the instruction that will be placed between `<|instruction-start|>` and `<|instruction-end|>` tags
* Part that needs to be rewritten will be marked with `<|rewrite-start|>` and `<|rewrite-end|>` tags.
* You need to examine the context of the documnt before and after parts that need to be rewritten.
* Your reply must start with acknowledgement of the task, followed by `<|rewrite-start|>`
* Your reply must end with `<|rewrite-end|>`
* Your reply must contain only the rewritten part. No additional commentary is required.
* That output will be copy-pasted instead of the original part.

<|document-start|>
{content}
<|document-end|>

Instruction:
<|instruction-start|>
{instruction}
<|instruction-end|>
""".format(
        filename=filename, content=content, instruction=instruction
    )
    m2 = "I understood I need to rewrite the text. Here is the new version\n<|rewrite-start|>\n"
    return [
        {"role": "system", "content": s},
        {"role": "user", "content": m1},
        {"role": "assistant", "content": m2},
    ]


def do_print(txt: str):
    txt = txt or "\n"
    print(txt, end="", flush=True)


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--prompt", type=str)
    args.add_argument("--file", type=str)

    ns = args.parse_args()

    file = ns.file
    prompt = ns.prompt
    assert file
    assert prompt

    text = Path(file).read_text()
    prompt = default_template(file, text, prompt)
    # print(prompt)
    return generate(prompt, do_print)


if __name__ == "__main__":
    main()
