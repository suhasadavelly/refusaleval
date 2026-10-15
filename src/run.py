"""Send each prompt in prompts.csv to the model in LM Studio and save the replies.

Usage:  python src/run.py            (uses config.yaml)
        python src/run.py other.yaml
Each run writes a new dated file in results/ and never overwrites an old one.
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompts(path, limit):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[:limit] if limit else rows


def sample_prompts(rows, n):
    """Pick n rows round-robin across categories (in CSV order), so every category is covered."""
    by_cat = {}
    for row in rows:
        by_cat.setdefault(row["category"], []).append(row)
    picked = []
    while len(picked) < n and any(by_cat.values()):
        for group in by_cat.values():
            if group and len(picked) < n:
                picked.append(group.pop(0))
    return picked


def ask_model(cfg, prompt):
    base = cfg["server"]["base_url"].rstrip("/")
    gen = cfg["generation"]
    body = {
        "model": cfg["model"]["name"],
        "temperature": gen["temperature"],
        "max_tokens": gen["max_tokens"],
        "seed": gen.get("seed"),
    }
    if cfg["model"]["mode"] == "chat":
        body["messages"] = [{"role": "user", "content": prompt}]
        r = requests.post(f"{base}/chat/completions", json=body, timeout=300)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    body["prompt"] = cfg["completion_template"].format(prompt=prompt)
    body["stop"] = cfg.get("stop")
    r = requests.post(f"{base}/completions", json=body, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["text"]


def main():
    cfg_path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
    cfg = load_config(cfg_path)
    sample = cfg["data"].get("sample")  # if set, overrides limit
    prompts = load_prompts(ROOT / cfg["data"]["prompts_file"], None if sample else cfg["data"].get("limit"))
    if sample:
        prompts = sample_prompts(prompts, sample)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = ROOT / "results" / f"{stamp}_{cfg['model']['name']}.jsonl"
    out_path.parent.mkdir(exist_ok=True)

    print(f"Running {len(prompts)} prompts -> {out_path.name}")
    with open(out_path, "x", encoding="utf-8") as out:  # "x" = fail if file exists; never overwrite results
        for i, row in enumerate(prompts, 1):
            try:
                reply, error = ask_model(cfg, row["prompt"]), None
            except Exception as e:  # keep going; record the failure
                reply, error = None, str(e)
            record = {
                **row,
                "reply": reply,
                "error": error,
                "model": cfg["model"]["name"],
                "mode": cfg["model"]["mode"],
                "settings": cfg["generation"],
                "time": datetime.now().isoformat(timespec="seconds"),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            status = "ERROR" if error else "ok"
            print(f"[{i}/{len(prompts)}] id={row.get('id')} {status}")

    print("Done.")


if __name__ == "__main__":
    main()
