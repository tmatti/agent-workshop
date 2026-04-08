import os
import subprocess
from typing import Dict, List

from litellm import completion


def _get_api_key() -> str:
    key_path = (os.environ.get("OPENROUTER_API_KEY_PATH") or "").strip()
    if not key_path:
        raise RuntimeError(
            "OPENROUTER_API_KEY_PATH is not set. Add it to `.env` with a 1Password secret reference."
        )
    result = subprocess.run(
        ["op", "read", key_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to read API key from 1Password: {result.stderr.strip()}")
    return result.stdout.strip()


def generate_response(
    messages: List[Dict],
    model: str = "openrouter/openai/gpt-4",
    max_tokens: int = 1024,
) -> str:
    """Call LLM to get response"""
    api_key = _get_api_key()

    response = completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        api_key=api_key,
    )
    return response.choices[0].message.content


def extract_code_block(response: str) -> str:
    """Extract code block from response"""

    if "```" not in response:
        return response

    code_block = response.split("```")[1].strip()

    if code_block.startswith("python"):
        code_block = code_block[6:]

    return code_block
