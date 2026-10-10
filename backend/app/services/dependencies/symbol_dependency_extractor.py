
import ast
from pathlib import PurePosixPath

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex



def extract_python_call_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    """Extract statically resolvable Python function and method calls."""

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    # Map local imported names to their actual declaration names and files.
    imported_symbols: dict[str, tuple[str, set[str]]] = {}

    def resolve_module(module: str | None, level: int) -> str | None:
        if level == 0:
            return module

        package_parts = list(PurePosixPath(source_file).parent.parts)
        levels_up = level - 1

        if levels_up > len(package_parts):
            return None

        if levels_up:
            package_parts = package_parts[:-levels_up]

        if module:
            package_parts.extend(module.split("."))

        return ".".join(package_parts) if package_parts else None

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        module = resolve_module(node.module, node.level)
        if not module:
            continue

        module_path = str(PurePosixPath(*module.split(".")))
        expected_paths = {
            module_path + ".py",
            str(PurePosixPath(module_path) / "__init__.py"),
        }

        for alias in node.names:
            local_name = alias.asname or alias.name
            imported_symbols[local_name] = (
                alias.name,
                expected_paths,
            )

    
    imported_modules: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue

        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]

            # For "import services.users", an unaliased reference
            # starts with "services", not "services.users".
            module_name = alias.name

            if alias.asname is None and "." in module_name:
                module_name = alias.name.split(".")[0]

            module_path = str(
                PurePosixPath(*module_name.split("."))
            )

            imported_modules[local_name] = {
                module_path + ".py",
                str(PurePosixPath(module_path) / "__init__.py"),
            }


    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, str, int]] = set()

    def visit(
        node: ast.AST,
        current_class: str | None = None,
        current_symbol: str | None = None,
    ) -> None:
        if isinstance(node, ast.ClassDef):
            current_class = node.name
            current_symbol = None
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            current_symbol = node.name

        if isinstance(node, ast.Call) and current_symbol is not None:
            source_candidates = [
                symbol
                for symbol in symbol_index.find_by_name(current_symbol)
                if symbol.file_path == source_file
                and (
                    (
                        current_class is not None
                        and symbol.kind == "method"
                        and symbol.parent_name == current_class
                    )
                    or (
                        current_class is None
                        and symbol.kind == "function"
                        and symbol.parent_name is None
                    )
                )
            ]

            target_candidates = []

            if isinstance(node.func, ast.Name):
                called_name = node.func.id

                if called_name in imported_symbols:
                    actual_name, expected_paths = imported_symbols[called_name]

                    target_candidates = [
                        symbol
                        for symbol in symbol_index.find_by_name(actual_name)
                        if symbol.file_path in expected_paths
                    ]
                else:
                    target_candidates = symbol_index.find_by_name(
                        called_name
                    )

            
            elif isinstance(node.func, ast.Attribute):
                # Resolve self.method() within the current class.
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "self"
                    and current_class is not None
                ):
                    target_candidates = [
                        symbol
                        for symbol in symbol_index.find_by_name(
                            node.func.attr
                        )
                        if symbol.kind == "method"
                        and symbol.file_path == source_file
                        and symbol.parent_name == current_class
                    ]

                # Resolve module.function() and module aliases.
                elif isinstance(node.func.value, ast.Name):
                    module_alias = node.func.value.id

                    if module_alias in imported_modules:
                        expected_paths = imported_modules[module_alias]

                        target_candidates = [
                            symbol
                            for symbol in symbol_index.find_by_name(
                                node.func.attr
                            )
                            if symbol.file_path in expected_paths
                        ]


            # Emit a dependency only when both ends are unambiguous.
            if len(source_candidates) == 1 and len(target_candidates) == 1:
                source = source_candidates[0]
                target = target_candidates[0]

                key = (
                    source.file_path,
                    source.name,
                    target.file_path,
                    node.lineno,
                )

                if key not in seen:
                    seen.add(key)
                    dependencies.append(
                        CodeDependency(
                            source_file=source.file_path,
                            target_file=target.file_path,
                            kind="calls",
                            source_symbol=source.name,
                            target_symbol=target.name,
                            line_number=node.lineno,
                        )
                    )

        for child in ast.iter_child_nodes(node):
            visit(child, current_class, current_symbol)

    visit(tree)
    return dependencies
