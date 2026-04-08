# CLAUDE.md

## Commands

```bash
uv sync          # install dependencies
uv run python main.py  # run the agent selector
```

## Architecture

`main.py` auto-discovers all agents in the `agents/` package at startup. Any module placed there that exposes a `NAME: str` and a `run()` function will appear in the menu automatically — no registration needed.

`llm_client.py` provides two shared utilities used by agents:
- `generate_response(messages, model, max_tokens)` — calls OpenRouter via LiteLLM
- `extract_code_block(response)` — strips markdown fences from LLM output

The API key is fetched at call time from 1Password using the `op` CLI. The `OPENROUTER_API_KEY_PATH` env var (loaded from `.env`) holds the `op://` secret reference — never the key itself.

Generated output from agents is written to `out/` (gitignored).

## Adding a new agent

Create `agents/<name>.py` with:
```python
NAME = "My Agent"

def run() -> None:
    ...
```

It will appear in the menu on next run.

After adding a new agent, update the projects section of the README accordingly
