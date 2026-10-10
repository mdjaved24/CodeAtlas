
from pathlib import Path, PurePosixPath

import tree_sitter_java as ts_java
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency


JAVA_LANGUAGE = Language(ts_java.language())



def _resolve_java_import(
    repository_root: Path,
    import_name: str,
) -> str | None:
    """Resolve a fully qualified Java type import inside common source roots."""

    if import_name.startswith("static "):
        return None

    parts = import_name.split(".")

    if not parts or any(not part.isidentifier() for part in parts):
        return None

    root = repository_root.resolve()
    relative_path = PurePosixPath(*parts).with_suffix(".java")

    # Support common Java project layouts.
    source_roots = (
        PurePosixPath("."),
        PurePosixPath("src/main/java"),
        PurePosixPath("src/test/java"),
    )

    for source_root in source_roots:
        candidate = source_root / relative_path
        target = root.joinpath(*candidate.parts)

        try:
            resolved_target = target.resolve()
            resolved_target.relative_to(root)
        except (OSError, ValueError, RuntimeError):
            continue

        if target.is_symlink() or not resolved_target.is_file():
            continue

        return candidate.as_posix()

    return None



def extract_java_import_dependencies(
    repository_root: Path,
    source_file: str,
    source_code: str,
) -> list[CodeDependency]:
    """Extract Java imports that resolve to repository source files."""

    parser = Parser(JAVA_LANGUAGE)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, int]] = set()

    def walk(node) -> None:
        if node.type == "import_declaration":
            # Static imports are deliberately excluded in this first version.
            declaration = source_bytes[
                node.start_byte : node.end_byte
            ].decode("utf-8").strip()

            if declaration.startswith("import static "):
                return

            # Extract the qualified name from:
            # import com.example.users.UserService;
            text = declaration.removeprefix("import").strip()
            text = text.removesuffix(";").strip()

            target_file = _resolve_java_import(
                repository_root,
                text,
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
