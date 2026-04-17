import json
import os
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import llm_client

NAME = "GAME Agent"

MODEL = "openrouter/openai/gpt-4o"


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass
class Prompt:
    messages: List[Dict] = field(default_factory=list)
    tools: List[Dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def _generate_response(prompt: Prompt) -> str:
    """Translate a Prompt into a string response using llm_client."""
    if not prompt.tools:
        return llm_client.generate_response(prompt.messages, model=MODEL)

    message = llm_client.generate_response_with_tools(
        prompt.messages, prompt.tools, model=MODEL
    )
    if message.tool_calls:
        tool = message.tool_calls[0]
        return json.dumps(
            {
                "tool": tool.function.name,
                "args": json.loads(tool.function.arguments),
            }
        )
    return message.content


# ---------------------------------------------------------------------------
# GAME framework classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Goal:
    priority: int
    name: str
    description: str


class Action:
    def __init__(
        self,
        name: str,
        function: Callable,
        description: str,
        parameters: Dict,
        terminal: bool = False,
    ):
        self.name = name
        self.function = function
        self.description = description
        self.terminal = terminal
        self.parameters = parameters

    def execute(self, **args) -> Any:
        return self.function(**args)


class ActionRegistry:
    def __init__(self):
        self.actions: Dict[str, Action] = {}

    def register(self, action: Action):
        self.actions[action.name] = action

    def get_action(self, name: str) -> Action | None:
        return self.actions.get(name)

    def get_actions(self) -> List[Action]:
        return list(self.actions.values())


class Memory:
    def __init__(self):
        self.items: List[Dict] = []

    def add_memory(self, memory: dict):
        self.items.append(memory)

    def get_memories(self, limit: int = None) -> List[Dict]:
        return self.items[:limit]

    def copy_without_system_memories(self):
        copy = Memory()
        copy.items = [m for m in self.items if m["type"] != "system"]
        return copy


class Environment:
    def execute_action(self, action: Action, args: dict) -> dict:
        try:
            result = action.execute(**args)
            return {
                "tool_executed": True,
                "result": result,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
        except Exception as e:
            return {
                "tool_executed": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


class AgentLanguage:
    def construct_prompt(
        self,
        actions: List[Action],
        environment: Environment,
        goals: List[Goal],
        memory: Memory,
    ) -> Prompt:
        raise NotImplementedError

    def parse_response(self, response: str) -> dict:
        raise NotImplementedError


class AgentFunctionCallingActionLanguage(AgentLanguage):
    def format_goals(self, goals: List[Goal]) -> List:
        sep = "\n-------------------\n"
        goal_instructions = "\n\n".join(
            [f"{g.name}:{sep}{g.description}{sep}" for g in goals]
        )
        return [{"role": "system", "content": goal_instructions}]

    def format_memory(self, memory: Memory) -> List:
        items = memory.get_memories()
        mapped = []
        for item in items:
            content = item.get("content") or json.dumps(item, indent=4)
            role = (
                "assistant" if item["type"] in ("assistant", "environment") else "user"
            )
            mapped.append({"role": role, "content": content})
        return mapped

    def format_actions(self, actions: List[Action]) -> List:
        return [
            {
                "type": "function",
                "function": {
                    "name": a.name,
                    "description": a.description[:1024],
                    "parameters": a.parameters,
                },
            }
            for a in actions
        ]

    def construct_prompt(
        self,
        actions: List[Action],
        environment: Environment,
        goals: List[Goal],
        memory: Memory,
    ) -> Prompt:
        messages = self.format_goals(goals) + self.format_memory(memory)
        tools = self.format_actions(actions)
        return Prompt(messages=messages, tools=tools)

    def parse_response(self, response: str) -> dict:
        try:
            return json.loads(response)
        except Exception:
            return {"tool": "terminate", "args": {"message": response}}


class Agent:
    def __init__(
        self,
        goals: List[Goal],
        agent_language: AgentLanguage,
        action_registry: ActionRegistry,
        generate_response: Callable[[Prompt], str],
        environment: Environment,
    ):
        self.goals = goals
        self.generate_response = generate_response
        self.agent_language = agent_language
        self.actions = action_registry
        self.environment = environment

    def construct_prompt(self, goals, memory, actions) -> Prompt:
        return self.agent_language.construct_prompt(
            actions=actions.get_actions(),
            environment=self.environment,
            goals=goals,
            memory=memory,
        )

    def get_action(self, response):
        invocation = self.agent_language.parse_response(response)
        action = self.actions.get_action(invocation["tool"])
        return action, invocation

    def should_terminate(self, response: str) -> bool:
        action_def, _ = self.get_action(response)
        return action_def.terminal

    def set_current_task(self, memory: Memory, task: str):
        memory.add_memory({"type": "user", "content": task})

    def update_memory(self, memory: Memory, response: str, result: dict):
        memory.add_memory({"type": "assistant", "content": response})
        memory.add_memory({"type": "environment", "content": json.dumps(result)})

    def run(
        self, user_input: str, memory: Memory = None, max_iterations: int = 50
    ) -> Memory:
        memory = memory or Memory()
        self.set_current_task(memory, user_input)

        for _ in range(max_iterations):
            prompt = self.construct_prompt(self.goals, memory, self.actions)
            print("Agent thinking...")
            response = self.generate_response(prompt)
            print(f"Agent Decision: {response}")

            action, invocation = self.get_action(response)
            result = self.environment.execute_action(action, invocation["args"])
            print(f"Action Result: {result}")

            self.update_memory(memory, response, result)

            if self.should_terminate(response):
                break

        return memory


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def _list_project_files() -> List[str]:
    return sorted(f for f in os.listdir(PROJECT_ROOT) if f.endswith(".py"))


def _read_project_file(name: str) -> str:
    target = os.path.normpath(os.path.join(PROJECT_ROOT, name))
    if not target.startswith(PROJECT_ROOT):
        return "Error: path is outside the project directory."
    with open(target) as f:
        return f.read()


def _build_agent() -> Agent:
    registry = ActionRegistry()
    registry.register(Action(
        name="list_project_files",
        function=_list_project_files,
        description="Lists all .py files in the project.",
        parameters={},
        terminal=False,
    ))
    registry.register(Action(
        name="read_project_file",
        function=_read_project_file,
        description="Reads a file from the project.",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        terminal=False,
    ))
    registry.register(Action(
        name="terminate",
        function=lambda message: f"{message}\nTerminating...",
        description="Terminates the session and prints the message to the user.",
        parameters={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": [],
        },
        terminal=True,
    ))

    goals = [
        Goal(priority=1, name="Gather Information",
             description="Read each file in the project"),
        Goal(priority=1, name="Terminate",
             description="Call the terminate action when you have read all the files "
                         "and provide the content of the README in the terminate message"),
    ]

    return Agent(
        goals=goals,
        agent_language=AgentFunctionCallingActionLanguage(),
        action_registry=registry,
        generate_response=_generate_response,
        environment=Environment(),
    )


def run() -> None:
    agent = _build_agent()
    final_memory = agent.run("Write a README for this project.")
    print(final_memory.get_memories())
