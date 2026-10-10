
import ast

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex


def extract_python_inheritance_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    """Extract confidently resolved Python class inheritance relationships."""
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError, TypeError):
        return []

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, str, str]] = set()

    # Track explicit imports so unrelated classes with the same name
    # aren't selected accidentally.
    imported_names: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names[alias.asname or alias.name] = alias.name

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        for base in node.bases:
            reference_name: str | None = None

            if isinstance(base, ast.Name):
                reference_name = base.id
            elif isinstance(base, ast.Attribute):
                # Handle a simple qualified reference such as models.Animal.
                parts: list[str] = []
                current = base

                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value

                if isinstance(current, ast.Name):
                    parts.append(current.id)
                    reference_name = ".".join(reversed(parts))

            if not reference_name:
                continue

            simple_name = reference_name.rsplit(".", 1)[-1]
            lookup_name = imported_names.get(simple_name, simple_name)
            candidates = [
                symbol
                for symbol in symbol_index.find_by_name(lookup_name)
                if symbol.kind == "class"
            ]

            # Only emit an edge when resolution is unique.
            if len(candidates) != 1:
                continue

            target = candidates[0]

            if target.file_path == source_file:
                # Same-file inheritance is valid; do not discard it.
                pass

            key = (
                source_file,
                target.file_path,
                node.name,
                target.name,
            )
            if key in seen:
                continue

            seen.add(key)
            dependencies.append(
                CodeDependency(
                    source_file=source_file,
                    target_file=target.file_path,
                    kind="inherits",
                    source_symbol=node.name,
                    target_symbol=target.name,
                    line_number=node.lineno,
                )
            )

    return dependencies
