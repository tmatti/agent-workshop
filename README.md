# AI Agents Certification

Projects and exercises completed as part of the [AI Agents Specialization](https://www.coursera.org/specializations/ai-agents) on Coursera.

## Projects

### Function Developer Agent (`agents/function_developer_agent.py`)

A multi-turn conversational agent that generates a Python function from a plain-English description. Given user input, it:

1. Writes an initial implementation
2. Adds comprehensive documentation
3. Generates `unittest` test cases
4. Saves the final output to the `out/` directory

### File Explorer Explorer Agent (`agents/file_explorer_agent.py`)

A ReAct-style agent loop that explores the project's files. Given a question, it autonomously lists and reads files to synthesize an answer, using three tools: `list_files`, `read_file`, and `terminate`.

## Setup

Requires Python 3.12 and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

### API Key

This project uses [OpenRouter](https://openrouter.ai/) via [LiteLLM](https://github.com/BerriAI/litellm). The API key is read from [1Password](https://1password.com/) at runtime using the `op` CLI.

Create a `.env` file:

```
OPENROUTER_API_KEY_PATH=op://Vault/Item/credential
```

Replace the path with your own 1Password secret reference.

## Usage

```bash
uv run python main.py
```

Select an agent from the menu and follow the prompts.
