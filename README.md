### Magaic

I couldn't find local LLM plugin for neovim which I liked. I made a new one.
I also don't like it, but as saying goes "There are many like it, but this one is mine."

### My plugin to talk with local ai served by ollama

Can either call completition checkpoint or chat. 
Also it called is wrapped in python script, because ollama binaryt loves to spit(as llama ought to) ansi codes.
Python script doesn't use 3rd party libraries, no venv is required.

For chat the following format is required

```
<SYS>this is system prompt
<USER>: this is what user is s
<AI>: this is ai
```

Note `: ` after talker -- both are optional


### Setting up with Lazy

  { "magaic", dir="~/src/nvim-plugins/magaic"},


### Usage:

First, we need to init it via `:MagaicShow` (`<leader>ms`). It's special buffer which is never saved.
Type someting. Use `:MagaicComplete`(`<leader>mr`) for usual complete (`/api/generate`) or use `:MagaicChat` (`<leader>mc`) to apply formatting for chat(`/api/chat`). 

Python script(`python/ollama-query.py`) should be in path
