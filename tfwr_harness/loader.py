"""Source loading helpers for TFWR harness runs.

Loading scripts and preparing module names is harness-only glue. The loaded
source is later paired with a synthetic builtin module so existing TFWR-style
imports continue to work under CPython.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import InvalidScenarioError


@dataclass(slots=True, frozen=True)
class LoadedScriptSource:
    """A script loaded from disk and prepared for validation or execution."""

    path: Path
    module_name: str
    text: str


@dataclass(slots=True, frozen=True)
class WorkspaceModuleSet:
    """Resolved importable `.py` modules that belong to one script workspace."""

    root_dir: Path
    module_paths: dict[str, Path]

    def resolve(self, module_name: str) -> Path | None:
        """Return the on-disk path for a workspace module, if present."""
        return self.module_paths.get(module_name)


def load_script_source(path: Path) -> LoadedScriptSource:
    """Load a script from disk and derive its module name from the filename."""
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise InvalidScenarioError(f"script not found: {resolved}")

    return LoadedScriptSource(
        path=resolved,
        module_name=resolved.stem,
        text=resolved.read_text(encoding="utf-8"),
    )


def discover_workspace_modules(entry_script: Path) -> WorkspaceModuleSet:
    """Discover importable sibling `.py` modules for one scenario entry script."""
    source = load_script_source(entry_script)
    root_dir = source.path.parent
    module_paths = {
        path.stem: path.resolve()
        for path in sorted(root_dir.glob("*.py"))
    }
    return WorkspaceModuleSet(root_dir=root_dir, module_paths=module_paths)
