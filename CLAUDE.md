# Project: refusal eval (OLMo 2 7B Instruct)

Measures how often OLMo 2 7B Instruct (`olmo-2-1124-7b-instruct`) refuses the questions in `data/prompts.csv`, served locally through LM Studio.

## How it works
`src/run.py` -> `results/*.jsonl` -> `src/judge.py` -> `src/report.py`
- Settings live in `config.yaml` (model, mode, temperature).
- The model is called through LM Studio's OpenAI-compatible `/v1/chat/completions` endpoint at localhost:1234.

## Rules
- Never overwrite or delete files in `results/`. Each run gets a new dated file.
- Keep model settings in `config.yaml`, never hardcoded.
- The refusal definition lives in `NOTES.md`. Ask before changing it.
- Make small changes and explain each diff.
- Python 3, minimal dependencies (requests, pyyaml).
