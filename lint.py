#!/usr/bin/env python
"""Run all code quality checks."""

import subprocess
import sys

def run_command(name, cmd):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Running {name}...")
    print('='*60)
    result = subprocess.run(cmd, shell=True)
    return result.returncode

def main():
    """Run all linting and type checking tools."""
    checks = [
        ("Black (formatter)", "black src/ tests/"),
        ("Ruff (linter)", "ruff check src/ tests/ --fix"),
        ("Mypy (type checker)", "mypy src/"),
        ("Pytest (tests)", "pytest"),
    ]

    failed = []
    for name, cmd in checks:
        if run_command(name, cmd) != 0:
            failed.append(name)

    print(f"\n{'='*60}")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("All checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
