import importlib
import pkgutil

import agents


def discover_agents():
    """Return list of (name, run) for every module in the agents package that exposes NAME and run."""
    found = []
    for mod_info in pkgutil.iter_modules(agents.__path__):
        mod = importlib.import_module(f"agents.{mod_info.name}")
        if hasattr(mod, "NAME") and hasattr(mod, "run"):
            found.append((mod.NAME, mod.run))
    return found


def main():
    available = discover_agents()

    if not available:
        print("No agents found in the agents/ package.")
        return

    print("\nAvailable agents:")
    for i, (name, _) in enumerate(available, 1):
        print(f"  {i}. {name}")

    print("\nSelect an agent (number): ", end="")
    choice = input().strip()

    if not choice.isdigit() or not (1 <= int(choice) <= len(available)):
        print("Invalid selection.")
        return

    _, run = available[int(choice) - 1]
    run()


if __name__ == "__main__":
    main()
