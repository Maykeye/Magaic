### Magaic

I couldn't find local LLM plugin for neovim which I liked. I made a new one.
I also don't like it, but as saying goes "There are many like it, but this one is mine."

### My plugin to talk with local ai served by llama.cpp

Can call only completion endpoint. Base model is expected.
As of now python used to to avoid PITA running curl or similar program.

### Setting up with Lazy

  { "magaic", dir="~/src/nvim-plugins/magaic"},


### Usage:

Open up the file to which the model will append text to the end. Then `:MagaicTee` (`<leader>mt`)

Python script(`python/llama.cpp-raq-query.py`) should be in `$PATH`
