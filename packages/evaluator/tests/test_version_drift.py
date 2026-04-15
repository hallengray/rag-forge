"""Cross-package version drift guard.

Every Python package in the rag-forge monorepo declares its version in
two places:

  1. ``pyproject.toml`` — consumed by the build backend and by
     ``pip show`` / ``pypi``.
  2. ``<package>/__init__.py`` ``__version__`` constant — consumed by
     any consumer that does ``import rag_forge_core; rag_forge_core.__version__``.

Cycle 3's PearMedica audit (2026-04-15) caught
``rag_forge_evaluator.__version__`` still reporting ``"0.1.0"`` even
though ``pip show`` correctly returned ``"0.2.1"``. The cause was a
release-prep miss: ``pyproject.toml`` was bumped, the constant was
forgotten. Users programmatically tagging their audit reports with the
tool version were recording the wrong version in their own records —
a trust paper-cut for a tool whose whole job is honest measurement.

This test asserts the two sources of truth match for every Python
package in the monorepo. It runs on every CI build, so any future
release that bumps one but not the other fails fast, not in a user
audit three cycles later.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGES_DIR = _REPO_ROOT / "packages"

_PACKAGES: list[tuple[str, str]] = [
    ("core", "rag_forge_core"),
    ("evaluator", "rag_forge_evaluator"),
    ("observability", "rag_forge_observability"),
]


def _read_pyproject_version(package_dir: Path) -> str:
    pyproject = package_dir / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    # Matches: version = "0.2.1"  (only the first [project] version)
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        msg = f"could not find version in {pyproject}"
        raise AssertionError(msg)
    return match.group(1)


def _read_init_version(package_dir: Path, module_name: str) -> str:
    init = package_dir / "src" / module_name / "__init__.py"
    text = init.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        msg = (
            f"{init} does not declare __version__. Every rag-forge "
            f"package must expose a __version__ constant so consumers "
            f"can programmatically introspect the installed version."
        )
        raise AssertionError(msg)
    return match.group(1)


@pytest.mark.parametrize(("subdir", "module_name"), _PACKAGES)
def test_package_version_matches_pyproject(subdir: str, module_name: str) -> None:
    """Assert ``__version__`` constant matches ``pyproject.toml`` version.

    Runs once per package. Failure message names which package drifted
    so a release-prep PR that forgets to bump one half gets an
    actionable error in CI rather than shipping a stale constant.
    """
    package_dir = _PACKAGES_DIR / subdir
    pyproject_version = _read_pyproject_version(package_dir)
    init_version = _read_init_version(package_dir, module_name)
    assert init_version == pyproject_version, (
        f"{module_name}.__version__ = {init_version!r} but "
        f"packages/{subdir}/pyproject.toml declares "
        f"{pyproject_version!r}. The two must stay in lockstep. Update "
        f"packages/{subdir}/src/{module_name}/__init__.py to match."
    )
