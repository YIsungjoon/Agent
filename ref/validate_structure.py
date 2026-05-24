#!/usr/bin/env python3
"""Validate the Fractal IRAC system folder shape."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent

REQUIRED = [
    "README.md",
    "MANIFEST.yaml",
    "architecture/OVERVIEW.md",
    "architecture/RUN_LIFECYCLE.md",
    "config/agents.yaml",
    "config/graph.yaml",
    "config/tool_policy.yaml",
    "prompts/root_agent.md",
    "prompts/subagent.md",
    "prompts/tool_use.md",
    "prompts/refinery.md",
    "schemas/workspace.schema.json",
    "tools/contracts.yaml",
    "tools/README.md",
    "runbooks/tool_enabled_irac_run.md",
    "examples/fire_compartment/workspace.seed.json",
    "examples/fire_compartment/README.md",
    "runtime/runs/README.md",
]


def main() -> int:
    missing = [item for item in REQUIRED if not (ROOT / item).exists()]
    if missing:
        print("missing:")
        for item in missing:
            print(f"- {item}")
        return 1
    print(f"ok: {len(REQUIRED)} required files present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

