#!/usr/bin/env bash
# use
# quick-test.sh 2..3
# or
# quick-test.sh 3..4
python ./llama.cpp-rewrite-with-chat.py --file gemini-sample-story.txt --range=$1 --prompt "Make Aiko turn to Kenji and blame him for making her heart going dokidoki too much. Three paragraphs"
