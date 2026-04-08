# Adapt Course Code

Adapt the course project code pasted by the user to fit this project's conventions.

## Project conventions to apply

- Use `generate_response` or `generate_response_with_tools` from `llm_client.py` instead of calling `litellm.completion` directly — the client handles 1Password key fetching and OpenRouter routing
- Every agent module must expose `NAME: str` and a `run() -> None` function so `main.py` auto-discovers it
- Agent files go in `agents/<name>.py`
- Generated output goes to `out/` (gitignored)
- Use `openrouter/openai/gpt-4o` as the default model string (passed to `llm_client`)

## What to do

1. Read the pasted code and identify what it does
2. Read the relevant existing files to understand current conventions (`llm_client.py`, an existing agent for reference)
3. Determine whether to create a new agent file or update an existing one
4. Write or update the agent, applying the conventions above
5. Do not update `main.py` — auto-discovery handles registration

Paste the course code below (or in the same message as `/adapt-course-code`).
