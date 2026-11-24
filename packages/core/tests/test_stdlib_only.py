import ast
import sys
from pathlib import Path

CORE_SOURCE = Path(__file__).parents[1] / "src"
ALLOWED_ROOTS = sys.stdlib_module_names | {"scibiom_core"}


def _imported_roots(source_file: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source_file.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            roots.add(node.module.split(".")[0])
    return roots


def test_core_imports_only_the_standard_library() -> None:
    source_files = sorted(CORE_SOURCE.rglob("*.py"))
    imported = {root for source_file in source_files for root in _imported_roots(source_file)}

    assert source_files
    assert imported <= ALLOWED_ROOTS, imported - ALLOWED_ROOTS
