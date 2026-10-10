
import ast
from pathlib import PurePosixPath

from app.schemas.source_parser import CodeSymbol
from app.schemas.symbol_resolution import SymbolResolution
from app.services.symbol_index import SymbolIndex


def _module_to_path(module: str) -> str:
    """Convert a Python module name into a repository-relative path."""
    return str(PurePosixPath(*module.split(".")))


def resolve_symbol(
    reference_name: str,
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> SymbolResolution:
    """Resolve a Python symbol reference using imports and indexed declarations.

    This initial implementation supports absolute Python imports and aliases.
    It deliberately avoids guessing when multiple declarations match.
    """

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return SymbolResolution(
            reference_name=reference_name,
            source_file=source_file,
            status="unresolved",
        )

    # Map a local name to its explicitly imported module and symbol.
    imports: dict[str, tuple[str, str]] = {}

    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            resolved_module = _resolve_import_module(
                module=node.module,
                level=node.level,
                source_file=source_file,
            )

            
    imports: dict[str, tuple[str, str]] = {}
    module_aliases: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            resolved_module = _resolve_import_module(
                module=node.module,
                level=node.level,
                source_file=source_file,
            )

            if resolved_module is None:
                continue

            for alias in node.names:
                local_name = alias.asname or alias.name
                imports[local_name] = (
                    resolved_module,
                    alias.name,
                )

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    # import services.user as user
                    module_aliases[alias.asname] = alias.name
                else:
                    # import services.user binds "services".
                    top_level = alias.name.split(".")[0]
                    module_aliases[top_level] = top_level

    
    if "." in reference_name:
        alias_name, symbol_name = reference_name.split(".", 1)
        module = module_aliases.get(alias_name)

        if module is not None:
            expected_path = _module_to_path(module) + ".py"

            candidates = [
                symbol
                for symbol in symbol_index.find_by_name(symbol_name)
                if symbol.file_path == expected_path
            ]

            return _build_result(
                reference_name,
                source_file,
                candidates,
            )

        # A qualified reference with an unknown module alias
        # must not fall back to a global name lookup.
        return _build_result(
            reference_name,
            source_file,
            [],
        )

    imported = imports.get(reference_name)

    if imported is not None:
        module, imported_name = imported

        # For "from module import Symbol", require the declaration to
        # match both the imported name and the expected module path.
        
        if imported_name:
            module_path = _module_to_path(module)

            expected_paths = {
                module_path + ".py",
                str(PurePosixPath(module_path) / "__init__.py"),
            }

            candidates = [
                symbol
                for symbol in symbol_index.find_by_name(imported_name)
                if symbol.file_path in expected_paths
            ]

            return _build_result(
                reference_name,
                source_file,
                candidates,
            )


        # Module imports do not directly identify a declaration.
        # Resolve only if the reference is a module alias itself.
        return _build_result(
            reference_name,
            source_file,
            [],
        )

    # Without a matching import, resolve only a unique name.
    # Do not choose arbitrarily among duplicate declarations.
    candidates = symbol_index.find_by_name(reference_name)

    return _build_result(
        reference_name,
        source_file,
        candidates,
    )


def _build_result(
    reference_name: str,
    source_file: str,
    candidates: list[CodeSymbol],
) -> SymbolResolution:
    if len(candidates) == 1:
        status = "resolved"
    elif len(candidates) > 1:
        status = "ambiguous"
    else:
        status = "unresolved"

    return SymbolResolution(
        reference_name=reference_name,
        source_file=source_file,
        status=status,
        candidates=candidates,
    )




def _resolve_import_module(
    module: str | None,
    level: int,
    source_file: str,
) -> str | None:
    """Resolve an import's module to a repository-relative module path."""

    source_path = PurePosixPath(source_file)

    # Absolute imports already identify their module directly.
    if level == 0:
        return module

    # For a file services/payment.py, the package is services.
    # For services/payments/processor.py, it is services.payments.
    package_parts = list(source_path.parent.parts)

    # One dot means current package; two dots mean its parent.
    levels_up = level - 1

    if levels_up > len(package_parts):
        return None

    if levels_up:
        package_parts = package_parts[:-levels_up]

    if module:
        package_parts.extend(module.split("."))

    if not package_parts:
        return None

    return ".".join(package_parts)

