# AI PPTX Translator

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)

Uses the latest Google GenAI models on LangChain to automate translation of Powerpoint decks into multiple languages.

## Description

I built this because it takes too much time to translate stuff at work. You will obviously have to resize the text boxes. 

## Features
- Uses an LLM for interpretation and translation.
- Contextual translation to improve accuracy and naturalness
- Parses Powerpoint documents to
- Comes in  a variety of common languages (I only ever use English, VIetnamese and Japanese)
- Has a chat box if you want to add even more context for it
- Batch processing & Async to improve speed
- Has a basic GUI to run off.


## Requirements

You need to run this with an API key you can yoink from Google AI Studio here: https://aistudio.google.com/apikey

Dependencies:
```sh
    pip install -r requirements.txt