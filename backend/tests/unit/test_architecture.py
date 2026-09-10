"""Import boundaries, enforced rather than reviewed.

The dependency direction this project relies on is easy to state and easy to
break by accident, usually with a single convenient import during a hurry.
Reviewing for it works until it does not; parsing for it keeps working.

    api  ->  services  ->  domain  <-  persistence
                                   <-  providers

The domain sits at the bottom and knows nothing about how it is delivered or
stored. Everything else may depend inwards, never outwards.

Checked by reading the AST rather than by importing the modules, so a
violation is reported as a violation instead of as an ImportError, and the
test does not need a database or a network to run.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "credit_radar"

INFRASTRUCTURE_PACKAGES = frozenset(
    {"fastapi", "starlette", "sqlalchemy", "alembic", "psycopg", "httpx", "respx"}
)
"""Third-party packages that carry a delivery or storage mechanism."""


def module_paths(*relative: str) -> list[Path]:
    roots = [PACKAGE_ROOT / part for part in relative] if relative else [PACKAGE_ROOT]
    return sorted(
        path
        for root in roots
        for path in root.rglob("*.py")
        if path.name != "__init__.py" or path.stat().st_size > 0
    )


def imported_modules(path: Path) -> set[str]:
    """Return every module name imported by a file, dotted paths included."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)

    return names


def top_level(module: str) -> str:
    return module.split(".", 1)[0]


def internal_layer(module: str) -> str | None:
    """Return the credit_radar layer a module belongs to, if any."""
    if not module.startswith("credit_radar."):
        return None
    return module.split(".")[1]


def relative(path: Path) -> str:
    return str(path.relative_to(PACKAGE_ROOT))


class TestDomainPurity:
    def test_the_domain_imports_no_infrastructure(self):
        # A domain that imports SQLAlchemy cannot be reasoned about without a
        # database, and a domain that imports FastAPI has an opinion about
        # HTTP. Both make the invariants here harder to test than they are.
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("domain")
            for module in sorted(imported_modules(path))
            if top_level(module) in INFRASTRUCTURE_PACKAGES
        ]

        assert violations == []

    def test_the_domain_imports_nothing_else_from_this_package(self):
        # Anything the domain needs from elsewhere is a sign the concept
        # belongs in the domain, or that the dependency is upside down.
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("domain")
            for module in sorted(imported_modules(path))
            if (layer := internal_layer(module)) is not None and layer != "domain"
        ]

        assert violations == []


class TestNoUpwardImports:
    @pytest.mark.parametrize("layer", ["domain", "persistence", "providers"])
    def test_lower_layers_do_not_import_the_layers_above_them(self, layer):
        forbidden = {"api", "services"}
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths(layer)
            for module in sorted(imported_modules(path))
            if internal_layer(module) in forbidden
        ]

        assert violations == []

    def test_providers_do_not_touch_persistence(self):
        # A provider's job ends at producing a domain object. Letting one
        # write to the database would put transaction boundaries inside an
        # adapter, where a retry or a parse failure could half-commit.
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("providers")
            for module in sorted(imported_modules(path))
            if internal_layer(module) == "persistence"
        ]

        assert violations == []


class TestDeliveryStaysAtTheEdge:
    def test_only_the_api_layer_imports_the_web_framework(self):
        web = {"fastapi", "starlette"}
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("domain", "services", "persistence", "providers")
            for module in sorted(imported_modules(path))
            if top_level(module) in web
        ]

        assert violations == []

    def test_only_providers_import_the_http_client(self):
        # An HTTP call from a service or a repository is an external
        # integration that skipped the anti-corruption layer.
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("domain", "services", "persistence", "api")
            for module in sorted(imported_modules(path))
            if top_level(module) in {"httpx", "respx"}
        ]

        assert violations == []

    def test_only_persistence_imports_the_orm(self):
        violations = [
            f"{relative(path)} imports {module}"
            for path in module_paths("domain", "providers")
            for module in sorted(imported_modules(path))
            if top_level(module) in {"sqlalchemy", "alembic", "psycopg"}
        ]

        assert violations == []


class TestTheCheckerItself:
    def test_it_actually_finds_the_modules(self):
        # A path typo would make every test above pass by inspecting nothing,
        # which is the failure mode of a test that reads the filesystem.
        assert len(module_paths("domain")) >= 2
        assert len(module_paths()) >= 10

    def test_it_detects_a_dotted_import(self):
        source = "from sqlalchemy.orm import Session\nimport httpx.aio\n"
        tree = ast.parse(source)
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)

        assert {top_level(n) for n in names} == {"sqlalchemy", "httpx"}
