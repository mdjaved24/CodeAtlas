
from pathlib import Path, PurePosixPath

import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency


TS_LANGUAGE = Language(ts_typescript.language_typescript())
TSX_LANGUAGE = Language(ts_typescript.language_tsx())


def _resolve_relative_import(
    repository_root: Path,
    source_file: str,
    import_path: str,
) -> str | None:
    """Resolve a relative TypeScript import to a repository file."""

    if not import_path.startswith("."):
        return None

    source = PurePosixPath(source_file)

    if (
        source.is_absolute()
        or ".." in source.parts
        or "\\" in source_file
    ):
        return None

    import_path_obj = PurePosixPath(import_path)

    if "\\" in import_path or import_path_obj.is_absolute():
        return None

    candidate = PurePosixPath(source.parent, import_path_obj)

    # Normalize relative components without allowing a root escape.
    normalized_parts: list[str] = []

    for part in candidate.parts:
        if part == "..":
            if not normalized_parts:
                return None
            normalized_parts.pop()
        elif part != ".":
            normalized_parts.append(part)

    candidate = PurePosixPath(*normalized_parts)

    candidates = [candidate]

    if candidate.suffix in (".js", ".jsx", ".mjs", ".cjs"):
        # TypeScript commonly imports JavaScript-compatible extensions.
        stem = candidate.with_suffix("")
        candidates.extend(
            stem.with_suffix(extension)
            for extension in (".ts", ".tsx")
        )
    elif not candidate.suffix:
        candidates.extend(
            PurePosixPath(str(candidate) + extension)
            for extension in (".ts", ".tsx", ".js", ".jsx", ".mts", ".cts")
        )
        candidates.extend(
            candidate / ("index" + extension)
            for extension in (".ts", ".tsx", ".js", ".jsx")
        )

    root = repository_root.resolve()

    for relative_path in candidates:
        if relative_path.is_absolute() or ".." in relative_path.parts:
            continue

        target = root.joinpath(*relative_path.parts)

        try:
            resolved_target = target.resolve()
            resolved_target.relative_to(root)
        except (OSError, ValueError, RuntimeError):
            continue

        if target.is_symlink():
            continue

        if resolved_target.is_file():
            return relative_path.as_posix()

    return None


def extract_typescript_import_dependencies(
    repository_root: Path,
    source_file: str,
    source_code: str,
) -> list[CodeDependency]:
    """Extract TypeScript imports that resolve inside the repository."""

    language = TSX_LANGUAGE if source_file.endswith(".tsx") else TS_LANGUAGE
    parser = Parser(language)

    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, int]] = set()

    def walk(node) -> None:
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")

            if source_node is not None:
                raw_path = source_bytes[
                    source_node.start_byte : source_node.end_byte
                ].decode("utf-8")

                import_path = (
                    raw_path[1:-1]
                    if len(raw_path) >= 2
                    and raw_path[0] in ("'", '"')
                    and raw_path[-1] == raw_path[0]
                    else ""
                )

                target_file = _resolve_relative_import(
                    repository_root,
                    source_file,
                    import_path,
                )

                if target_file is not None:
                    line_number = node.start_point.row + 1
                    key = (source_file, target_file, line_number)

                    if key not in seen:
                        seen.add(key)
                        dependencies.append(
                            CodeDependency(
                                source_file=source_file,
                                target_file=target_file,
                                kind="imports",
                                line_number=line_number,
                            )
                        )

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return dependencies
