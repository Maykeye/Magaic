#!/usr/bin/env python
from typing import Optional, TextIO
import requests
import json
import os
import argparse
from pathlib import Path

URL_COMPLETION = (
    f"http://localhost:{os.environ.get('LLAMA_CPP_PORT', 10000)}/completion"
)


def generate(prompt: str, output: Optional[TextIO]):
    request_data = {
        "prompt": prompt,
        "n_predict": 64,
        "stream": True,
    }

    print(prompt, end="")

    total_response = ""
    response = requests.post(URL_COMPLETION, json=request_data, stream=True)
    response.raise_for_status()
    for bdata in response.iter_lines():
        data = bdata.decode().strip().removeprefix("data: ")
        if not data:
            continue
        content = json.loads(data)["content"]
        total_response += content
        print(content, flush=True, end="")
        if output is not None:
            print(content, flush=True, end="", file=output)
    if not total_response.endswith("\n"):
        print()


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--prompt", type=str)
    args.add_argument("--file", type=str)

    ns = args.parse_args()
    assert ns.prompt is None or ns.file is None

    if ns.prompt:
        return generate(ns.prompt, None)
    elif ns.file:
        prompt = Path(ns.file).read_text()
        nonl = prompt.removesuffix("\n")
        if prompt != nonl:
            Path(ns.file).write_text(nonl)

        with open(ns.file, "a") as output:
            generate(nonl, output)
        return

    raise ValueError("--prompt <raw-promp[t> or --file <append-to-this-file> expected ")


if __name__ == "__main__":
    main()
