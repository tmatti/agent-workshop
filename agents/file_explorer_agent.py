import json
import os

from llm_client import generate_response_with_tools

NAME = "File Explorer"

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

SYSTEM_PROMPT = """You are an AI agent that can perform tasks by using available tools.

If a user asks about files, documents, or content, first list the files before reading them.
When you have enough information to answer the user, respond with a plain text summary — no tool call needed."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Returns a list of files in the project directory.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the content of a file in the project directory.",
            "parameters": {
                "type": "object",
                "properties": {"file_name": {"type": "string"}},
                "required": ["file_name"],
            },
        },
    },
]


def list_files() -> list:
    return os.listdir(PROJECT_ROOT)


def read_file(file_name: str) -> str:
    target = os.path.normpath(os.path.join(PROJECT_ROOT, file_name))
    if not target.startswith(PROJECT_ROOT):
        return "Error: path is outside the project directory."
    try:
        with open(target) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: {file_name} not found."
    except Exception as e:
        return f"Error: {e}"


tool_functions = {
    "list_files": list_files,
    "read_file": read_file,
}


def run() -> None:
    print("\nWhat would you like me to do?")
    user_task = input("Your task: ").strip()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for _ in range(10):
        print("Agent thinking...")
        message = generate_response_with_tools(messages, tools)

        # No tool calls — final answer
        if not message.tool_calls:
            print(f"\n{message.content}")
            break

        # Append assistant message and process each tool call
        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"  -> {name}({args})")
            result = tool_functions[name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })
