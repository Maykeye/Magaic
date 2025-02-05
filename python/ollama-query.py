#!/usr/bin/python
import json
import requests
import sys

def raw(prompt):
    url = 'http://localhost:11434/api/generate'
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    #open("/tmp/last.prompt", "w").write(json.dumps(payload, indent=2))

    response = requests.post(url, json=payload)

    if response.ok:
        print(response.json()["response"])
    else:
        print(f"ERR {response.status_code}: {response.text}")

def chat(prompt: str):
    """ replace <USER> with user, replace <AI> with ai, replace <SYS> with system"""
    url = 'http://localhost:11434/api/chat'

    lines: list[str] = prompt.splitlines(keepends=True)
    messages = []
    roles = {"<USR>": "user", 
             "<USER>": "user", 
             "<AI>": "assistant", 
             "<SYS>": "system", 
             "<SYSTEM>":"system"}

    for line in lines:
        for prefix, role in roles.items():
            if not line.startswith(prefix):
                continue
            
            line = line.removeprefix(prefix)
            line = line.removeprefix(":") # Allow some trailing garbo
            line = line.removeprefix(" ") # Allow some trailing garbo
            messages.append({"role": role, "content": line})
            break
        else:
            # didn't find a role. 
            if messages:
                messages[-1]["content"] += line
                continue
            else: # if no role defined, assume user is talking
                messages.append({"role": "user", "content": line})

    prompt = json.dumps(messages)
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    #open("/tmp/last.prompt", "w").write(json.dumps(payload, indent=2))
    response = requests.post(url, json=payload)

    if response.ok:
        print(response.json()["message"]["content"])
    else:
        print(f"ERR {response.status_code}: {response.text}")

model = sys.argv[1]
mode = sys.argv[2]
if mode == "raw":
    raw(prompt = sys.argv[3])
elif mode == "chat":
    chat(prompt = sys.argv[3])
else:
    raise ValueError("invalid query mode")


exit()
