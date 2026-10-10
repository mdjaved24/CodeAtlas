
from pathlib import Path, PurePosixPath

from app.schemas.source_parser import ParseResult
from app.services.file_selection import FileSelection

from app.services.parsers.python_parser import parse_python_source
from app.services.parsers.javascript_parser import parse_javascript_source
from app.services.parsers.typescript_parser import parse_typescript_source
from app.services.parsers.java_parser import parse_java_source
from app.services.parsers.csharp_parser import parse_csharp_source


PARSER_BY_LANGUAGE = {
    "python": parse_python_source,
    "javascript": parse_javascript_source,
    "typescript": parse_typescript_source,
    "java": parse_java_source,
    "csharp": parse_csharp_source,
}


def parse_selected_source_files(
    repository_root: Path,
    manifest: list[FileSelection],
) -> list[ParseResult]:
    """Parse selected source files using their language-specific parsers.

    Files are processed independently so that a failure in one file
    does not prevent other selected files from being parsed.
    """

    root = repository_root.resolve()
    results: list[ParseResult] = []

    for item in manifest:
        if not item.selected:
            continue

        language = item.language
        
        # Documentation, configuration, and other non-source files
        # may be selected but have no parser language.
        if language is None:
            continue

        parser_function = PARSER_BY_LANGUAGE.get(language)

        # Ignore languages that do not have a registered parser.
        if parser_function is None:
            continue

        try:
            relative_path = PurePosixPath(item.path)

            # Reject absolute paths, traversal, and Windows separators.
            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
                or "\\" in item.path
            ):
                raise ValueError("Unsafe repository-relative path")

            source_path = root.joinpath(*relative_path.parts)

            # Reject a symbolic link at the selected path.
            if source_path.is_symlink():
                raise ValueError("Symbolic links are not supported")

            resolved_path = source_path.resolve()

            # Defense in depth: the resolved path must remain in the repo.
            resolved_path.relative_to(root)

            if not resolved_path.is_file():
                raise FileNotFoundError(
                    "Selected source file not found"
                )

            source = resolved_path.read_text(encoding="utf-8")

            result = parser_function(
                source=source,
                file_path=item.path,
            )

        except Exception as exc:
            # Isolate failures to this file without exposing file contents.
            result = ParseResult(
                file_path=item.path,
                language=language,
                status="failed",
                symbols=[],
                has_syntax_errors=False,
                diagnostics=[
                    f"File parsing failed: {type(exc).__name__}"
                ],
            )

        results.append(result)

    return results


def parse_selected_python_files(
    repository_root: Path,
    manifest: list[FileSelection],
) -> list[ParseResult]:
    """Backward-compatible entry point for the existing upload workflow.

    Despite its historical name, this now processes every supported
    language in the selected manifest.
    """

    return parse_selected_source_files(
        repository_root=repository_root,
        manifest=manifest,
    )
