
from pathlib import Path, PurePosixPath

from app.schemas.dependency import CodeDependency
from app.schemas.source_parser import ParseResult
from app.services.dependencies.import_dependency_extractor import (
    extract_python_import_dependencies,
)
from app.services.dependencies.symbol_dependency_extractor import (
    extract_python_call_dependencies,
)
from app.services.dependencies.javascript_import_dependency_extractor import (
    extract_javascript_import_dependencies,
)
from app.services.dependencies.typescript_import_dependency_extractor import (
    extract_typescript_import_dependencies,
)
from app.services.dependencies.java_import_dependency_extractor import (
    extract_java_import_dependencies,
)
from app.services.dependencies.csharp_import_dependency_extractor import (
    extract_csharp_import_dependencies,
)
from app.services.dependencies.inheritance_dependency_extractor import (
    extract_python_inheritance_dependencies,
)
from app.services.dependencies.javascript_inheritance_dependency_extractor import (
    extract_javascript_inheritance_dependencies,
)
from app.services.dependencies.typescript_inheritance_dependency_extractor import (
    extract_typescript_inheritance_dependencies,
)
from app.services.dependencies.java_inheritance_dependency_extractor import (
    extract_java_inheritance_dependencies,
)
from app.services.dependencies.csharp_inheritance_dependency_extractor import (
    extract_csharp_inheritance_dependencies,
)

from app.services.symbols.symbol_index import SymbolIndex


import logging

logger = logging.getLogger(__name__)


def extract_repository_dependencies(
    repository_root: Path,
    parse_results: list[ParseResult],
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    """Combine import and call dependencies from successfully parsed files."""

    root = repository_root.resolve()
    dependencies: list[CodeDependency] = []
    validated_source_files: dict[str, str] = {}

    # Pass 1: Validate and read all supported source files.
    validated_results: list[tuple[ParseResult, str]] = []

    for result in parse_results:
        if result.status not in ("success", "partial"):
            continue

        if result.language not in (
            "python",
            "javascript",
            "typescript",
            "java",
            "csharp",
        ):
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

        except (OSError, ValueError, RuntimeError):
            continue

        normalized_path = relative_path.as_posix()
        validated_source_files[normalized_path] = source_code
        validated_results.append((result, source_code))

        for result, source_code in validated_results:
            if result.language == "python":
                try:
                    dependencies.extend(
                        extract_python_import_dependencies(
                            repository_root=root,
                            source_file=result.file_path,
                            source_code=source_code,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

                try:
                    dependencies.extend(
                        extract_python_call_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

                try:
                    dependencies.extend(
                        extract_python_inheritance_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

            elif result.language == "javascript":
                try:
                    dependencies.extend(
                        extract_javascript_import_dependencies(
                            repository_root=root,
                            source_file=result.file_path,
                            source_code=source_code,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )               

                try:
                    dependencies.extend(
                        extract_javascript_inheritance_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

            elif result.language == "typescript":
                try:
                    dependencies.extend(
                        extract_typescript_import_dependencies(
                            repository_root=root,
                            source_file=result.file_path,
                            source_code=source_code,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

                try:
                    dependencies.extend(
                        extract_typescript_inheritance_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

            elif result.language == "java":
                try:
                    dependencies.extend(
                        extract_java_import_dependencies(
                            repository_root=root,
                            source_file=result.file_path,
                            source_code=source_code,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )

                
                try:
                    dependencies.extend(
                        extract_java_inheritance_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )
            

            elif result.language == "csharp":
                try:
                    dependencies.extend(
                        extract_csharp_import_dependencies(
                            repository_root=root,
                            source_file=result.file_path,
                            source_code=source_code,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )
                
                try:
                    dependencies.extend(
                        extract_csharp_inheritance_dependencies(
                            source_file=result.file_path,
                            source_code=source_code,
                            symbol_index=symbol_index,
                            source_files=validated_source_files,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Dependency extraction failed for %s in %s",
                        result.file_path,
                        result.language,
                    )


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
