import ast
from pathlib import Path, PurePosixPath

from app.schemas.dependency import CodeDependency


def _module_to_relative_path(module: str) -> str:
    """Convert a dotted Python module into a repository-relative path."""
    return str(PurePosixPath(*module.split(".")))


def _resolve_module_path(
    module: str,
    source_file: str,
    level: int = 0,
) -> str | None:
    """Resolve an absolute or relative Python module to a .py path."""

    if level == 0:
        parts = module.split(".") if module else []
    else:
        source_parent = list(PurePosixPath(source_file).parent.parts)
        levels_up = level - 1

        if levels_up > len(source_parent):
            return None

        if levels_up:
            source_parent = source_parent[:-levels_up]

        parts = source_parent
        if module:
            parts = parts + module.split(".")

    if not parts:
        return None

    return str(PurePosixPath(*parts)) + ".py"


def extract_python_import_dependencies(
    repository_root: Path,
    source_file: str,
    source_code: str,
) -> list[CodeDependency]:
    """Extract imports that resolve to Python files inside the repository.

    This function parses source code without executing it.
    """

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    root = repository_root.resolve()
    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, int]] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_path = _resolve_module_path(
                module=node.module or "",
                source_file=source_file,
                level=node.level,
            )

            if module_path is None:
                continue

            # "from package import symbol" may refer to either a module
            # or a symbol exported by the package. Check both file forms.
            candidate_paths = [
                module_path,
                str(PurePosixPath(module_path) / "__init__.py"),
            ]

        elif isinstance(node, ast.Import):
            candidate_paths = [
                _resolve_module_path(alias.name, source_file)
                for alias in node.names
            ]
            candidate_paths = [
                path for path in candidate_paths if path is not None
            ]

        else:
            continue

        for candidate in candidate_paths:
            relative_path = PurePosixPath(candidate)

            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
                or "\\" in candidate
            ):
                continue

            target = root.joinpath(*relative_path.parts).resolve()

            try:
                target.relative_to(root)
            except ValueError:
                continue

            if not target.is_file() or target.suffix != ".py":
                continue

            key = (source_file, candidate, node.lineno)
            if key in seen:
                continue

            seen.add(key)
            dependencies.append(
                CodeDependency(
                    source_file=source_file,
                    target_file=candidate,
                    kind="imports",
                    line_number=node.lineno,
                )
            )

    return dependencies
