#!/bin/bash
# load .env for local dev (optional)
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# install deps (only first time)
# pip install -r requirements.txt

python3 bot.py
