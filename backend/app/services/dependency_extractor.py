
from pathlib import Path, PurePosixPath

from app.schemas.dependency import CodeDependency
from app.schemas.source_parser import ParseResult
from app.services.import_dependency_extractor import (
    extract_python_import_dependencies,
)
from app.services.symbol_dependency_extractor import (
    extract_python_call_dependencies,
)
from app.services.symbol_index import SymbolIndex


def extract_repository_dependencies(
    repository_root: Path,
    parse_results: list[ParseResult],
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    """Combine import and call dependencies from successfully parsed files."""

    root = repository_root.resolve()
    dependencies: list[CodeDependency] = []

    for result in parse_results:
        if result.status not in ("success", "partial"):
            continue

        if result.language != "python":
            continue

        relative_path = PurePosixPath(result.file_path)

        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or "\\" in result.file_path
        ):
            continue

        try:
            source_path = root.joinpath(*relative_path.parts)
            resolved_path = source_path.resolve()
            resolved_path.relative_to(root)

            if source_path.is_symlink() or not resolved_path.is_file():
                continue

            source_code = resolved_path.read_text(encoding="utf-8")

        except (OSError, ValueError):
            # One inaccessible file must not stop processing the repository.
            continue

        try:
            dependencies.extend(
                extract_python_import_dependencies(
                    repository_root=root,
                    source_file=result.file_path,
                    source_code=source_code,
                )
            )
        except Exception:
            # Isolate unexpected failures in import extraction.
            pass

        try:
            dependencies.extend(
                extract_python_call_dependencies(
                    source_file=result.file_path,
                    source_code=source_code,
                    symbol_index=symbol_index,
                )
            )
        except Exception:
            # Isolate unexpected failures in call extraction.
            pass

    # Keep each distinct relationship once while preserving order.
    unique_dependencies: list[CodeDependency] = []
    seen: set[tuple] = set()

    for dependency in dependencies:
        key = (
            dependency.source_file,
            dependency.target_file,
            dependency.kind,
            dependency.source_symbol,
            dependency.target_symbol,
            dependency.line_number,
        )

        if key not in seen:
            seen.add(key)
            unique_dependencies.append(dependency)

    return unique_dependencies
