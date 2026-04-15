"""Cross-package version drift guard.

Every Python package in the rag-forge monorepo declares its version in
two places:

  1. ``pyproject.toml`` — consumed by the build backend and by
     ``pip show`` / ``pypi``.
  2. ``<package>/__init__.py`` ``__version__`` constant — consumed by
     any consumer that does
     ``import rag_forge_core; rag_forge_core.__version__``.

Cycle 3's PearMedica audit (2026-04-15) caught
``rag_forge_evaluator.__version__`` still reporting ``"0.1.0"`` even
though ``pip show`` correctly returned ``"0.2.1"``. The cause was a
release-prep miss: ``pyproject.toml`` was bumped, the constant was
forgotten. Users programmatically tagging their audit reports with
the tool version were recording the wrong version in their own
records — a trust paper-cut for a tool whose whole job is honest
measurement.

This test asserts the two sources of truth match for every Python
package in the monorepo. It runs on every CI build, so any future
release that bumps one but not the other fails fast, not in a user
audit three cycles later.

**Auto-discovery:** packages are discovered at collection time by
walking ``packages/*/pyproject.toml`` — not a hand-maintained list.
CodeRabbit on PR #37 pointed out that a hardcoded inventory lets new
packages silently bypass the drift check if a contributor forgets to
add them. Auto-discovery removes that failure mode.

**Tolerant parsing:** ``pyproject.toml`` is parsed with the stdlib
``tomllib`` (``tomli`` on Python < 3.11) to survive tables that appear
before ``[project]`` (e.g. ``[tool.bump]``). The ``__version__``
regex accepts both single and double quotes and tolerates type
annotations like ``__version__: str = "..."``.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGES_DIR = _REPO_ROOT / "packages"

# Matches ``__version__ = "..."``, ``__version__ = '...'``,
# ``__version__: str = "..."``, or any combination thereof. Anchored
# to the start of a line so it ignores the constant appearing inside
# a docstring or comment block.
_VERSION_PATTERN = re.compile(
    r'^__version__\s*(?::\s*[\w\[\], .]+)?\s*=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)


def _discover_packages() -> list[tuple[str, str]]:
    """Walk ``packages/*`` and return ``(subdir, module_name)`` pairs.

    A directory counts as a Python package if it has ``pyproject.toml``
    at its root and exactly one subdirectory under ``src/``. The module
    name is that subdirectory.

    TypeScript packages (``packages/cli``, ``packages/mcp``,
    ``packages/shared``) have no ``src/<python_module>`` layout so
    they are skipped silently.
    """
    discovered: list[tuple[str, str]] = []
    for package_dir in sorted(_PACKAGES_DIR.iterdir()):
        if not package_dir.is_dir():
            continue
        if not (package_dir / "pyproject.toml").exists():
            continue
        src_dir = package_dir / "src"
        if not src_dir.is_dir():
            continue
        module_dirs = [
            child
            for child in src_dir.iterdir()
            if child.is_dir() and (child / "__init__.py").exists()
        ]
        if len(module_dirs) != 1:
            continue
        discovered.append((package_dir.name, module_dirs[0].name))
    return discovered


_PACKAGES = _discover_packages()


def _read_pyproject_version(package_dir: Path) -> str:
    """Read ``[project].version`` from ``pyproject.toml`` via ``tomllib``.

    Using the stdlib TOML parser avoids brittle regex assumptions
    about section ordering — a ``[tool.X] version = "..."`` preceding
    ``[project]`` would have fooled the old first-match regex.
    """
    pyproject_path = package_dir / "pyproject.toml"
    with pyproject_path.open("rb") as fh:
        data = tomllib.load(fh)
    try:
        version = data["project"]["version"]
    except KeyError as exc:
        msg = f"{pyproject_path} has no [project].version key"
        raise AssertionError(msg) from exc
    if not isinstance(version, str):
        msg = f"{pyproject_path}: [project].version is not a string"
        raise AssertionError(msg)
    return version


def _read_init_version(package_dir: Path, module_name: str) -> str:
    """Extract ``__version__`` from a module's ``__init__.py``.

    The regex accepts ``__version__ = "x"``, ``__version__ = 'x'``,
    and ``__version__: str = "x"`` — all three are valid Python and
    all three appear in the wild. CodeRabbit on PR #37 pointed out the
    original pattern only matched double-quoted unannotated form.
    """
    init_path = package_dir / "src" / module_name / "__init__.py"
    text = init_path.read_text(encoding="utf-8")
    match = _VERSION_PATTERN.search(text)
    if not match:
        msg = (
            f"{init_path} does not declare __version__ in a recognised "
            f"form. Every rag-forge package must expose a __version__ "
            f"constant so consumers can programmatically introspect "
            f"the installed version."
        )
        raise AssertionError(msg)
    return match.group(1)


def test_at_least_one_python_package_discovered() -> None:
    """Sanity guard: if auto-discovery finds zero packages, the rest
    of this suite becomes a no-op and silently passes. Fail loud
    instead so a broken discovery walk is visible immediately.
    """
    assert _PACKAGES, (
        f"Auto-discovery found no Python packages under {_PACKAGES_DIR}. "
        f"Either the repo layout changed or _discover_packages() is "
        f"broken — either way the drift guard is not running."
    )


@pytest.mark.parametrize(("subdir", "module_name"), _PACKAGES)
def test_package_version_matches_pyproject(subdir: str, module_name: str) -> None:
    """Assert ``__version__`` constant matches ``pyproject.toml`` version.

    Runs once per discovered package. Failure message names which
    package drifted so a release-prep PR that forgets to bump one
    half gets an actionable error in CI rather than shipping a stale
    constant.
    """
    package_dir = _PACKAGES_DIR / subdir
    pyproject_version = _read_pyproject_version(package_dir)
    init_version = _read_init_version(package_dir, module_name)
    assert init_version == pyproject_version, (
        f"{module_name}.__version__ = {init_version!r} but "
        f"packages/{subdir}/pyproject.toml declares "
        f"{pyproject_version!r}. The two must stay in lockstep. "
        f"Update packages/{subdir}/src/{module_name}/__init__.py "
        f"to match."
    )
