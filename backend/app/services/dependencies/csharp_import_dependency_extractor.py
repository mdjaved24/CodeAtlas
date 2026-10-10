
from pathlib import Path, PurePosixPath

import tree_sitter_c_sharp as ts_csharp
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency


CSHARP_LANGUAGE = Language(ts_csharp.language())


def _is_safe_repository_file(root: Path, relative_path: str) -> bool:
    """Return True when a relative path resolves to a regular file inside root."""
    path = PurePosixPath(relative_path)

    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in relative_path
    ):
        return False

    candidate = root.joinpath(*path.parts)

    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except (OSError, ValueError, RuntimeError):
        return False

    return not candidate.is_symlink() and resolved.is_file()


def _extract_namespace_names(source_code: str) -> set[str]:
    """Extract declared namespace names without executing C# code."""
    parser = Parser(CSHARP_LANGUAGE)
    tree = parser.parse(source_code.encode("utf-8"))
    namespaces: set[str] = set()

    def walk(node) -> None:
        if node.type == "namespace_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = name_node.text.decode("utf-8").strip()
                if name:
                    namespaces.add(name)

        elif node.type == "file_scoped_namespace_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = name_node.text.decode("utf-8").strip()
                if name:
                    namespaces.add(name)

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return namespaces


def _extract_using_names(source_code: str) -> list[tuple[str, int]]:
    """Extract ordinary namespace using directives and their line numbers."""
    parser = Parser(CSHARP_LANGUAGE)
    tree = parser.parse(source_code.encode("utf-8"))
    source_bytes = source_code.encode("utf-8")
    imports: list[tuple[str, int]] = []

    def walk(node) -> None:
        if node.type == "using_directive":
            # Static imports and alias directives need different resolution rules.
            text = source_bytes[node.start_byte:node.end_byte].decode(
                "utf-8"
            ).strip()

            if text.startswith("using static "):
                return

            declaration = text.removeprefix("using").strip()
            declaration = declaration.removesuffix(";").strip()

            # Avoid treating aliases (using Alias = Namespace.Type;)
            # as ordinary namespace imports.
            if "=" in declaration:
                return

            if declaration and all(
                part.isidentifier() for part in declaration.split(".")
            ):
                imports.append((declaration, node.start_point.row + 1))

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return imports


def extract_csharp_import_dependencies(
    repository_root: Path,
    source_file: str,
    source_code: str,
) -> list[CodeDependency]:
    """Extract namespace imports that resolve to files in this repository."""
    root = repository_root.resolve()

    source_path = PurePosixPath(source_file)
    if (
        source_path.is_absolute()
        or ".." in source_path.parts
        or "\\" in source_file
    ):
        return []

    if not source_code.strip():
        return []

    imports = _extract_using_names(source_code)
    if not imports:
        return []

    # Scan repository C# files. Never execute or compile repository code.
    namespace_to_files: dict[str, list[str]] = {}
    for path in root.rglob("*.cs"):
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError, RuntimeError):
            continue

        if path.is_symlink() or not resolved.is_file():
            continue

        try:
            relative_path = path.relative_to(root).as_posix()
            if not _is_safe_repository_file(root, relative_path):
                continue
            code = resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError, RuntimeError):
            continue

        for namespace in _extract_namespace_names(code):
            namespace_to_files.setdefault(namespace, []).append(relative_path)

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, int]] = set()

    for namespace, line_number in imports:
        for target_file in namespace_to_files.get(namespace, []):
            if target_file == source_file:
                continue

            key = (source_file, target_file, line_number)
            if key in seen:
                continue

            seen.add(key)
            dependencies.append(
                CodeDependency(
                    source_file=source_file,
                    target_file=target_file,
                    kind="imports",
                    line_number=line_number,
                )
            )

    return dependencies
