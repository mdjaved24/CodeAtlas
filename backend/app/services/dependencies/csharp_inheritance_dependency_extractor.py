
import tree_sitter_c_sharp as ts_csharp
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex


CSHARP_LANGUAGE = Language(ts_csharp.language())



def _extract_csharp_namespaces(source_code: str) -> set[str]:
    """Extract namespace declarations from C# source using Tree-sitter."""
    parser = Parser(CSHARP_LANGUAGE)
    tree = parser.parse(source_code.encode("utf-8"))

    if tree.root_node.has_error:
        return set()

    namespaces: set[str] = set()

    def walk(node) -> None:
        if node.type in (
            "namespace_declaration",
            "file_scoped_namespace_declaration",
        ):
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                namespaces.add(name_node.text.decode("utf-8"))

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return namespaces



def _build_csharp_namespace_index(
    symbol_index: SymbolIndex,
    source_files: dict[str, str],
) -> dict[str, set[str]]:
    """Map declared namespaces to indexed source files."""
    namespace_to_files: dict[str, set[str]] = {}

    indexed_files = {
        symbol.file_path.replace("\\", "/")
        for symbol in symbol_index.all_symbols()
    }

    for file_path in indexed_files:
        source_code = source_files.get(file_path)
        if source_code is None:
            continue

        for namespace in _extract_csharp_namespaces(source_code):
            namespace_to_files.setdefault(namespace, set()).add(file_path)

    return namespace_to_files


def extract_csharp_inheritance_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
    source_files: dict[str, str] | None = None,
) -> list[CodeDependency]:
    parser = Parser(CSHARP_LANGUAGE)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    if tree.root_node.has_error:
        return []

    source_files = source_files or {}
    normalized_source_files = {
        path.replace("\\", "/"): code
        for path, code in source_files.items()
    }

    namespace_to_files = _build_csharp_namespace_index(
        symbol_index,
        normalized_source_files,
    )

    classes: list[tuple[str, str, int]] = []

    def walk_classes(node) -> None:
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")

            base_list = next(
                (
                    child
                    for child in node.named_children
                    if child.type == "base_list"
                ),
                None,
            )

            if name_node is not None and base_list is not None:
                class_name = name_node.text.decode("utf-8")

                for base_node in base_list.named_children:
                    # A base list may contain the base class and interfaces.
                    # This extractor handles class inheritance only.
                    if base_node.type in (
                        "identifier",
                        "generic_name",
                        "qualified_name",
                        "alias_qualified_name",
                    ):
                        qualified_base_name = (
                            base_node.text.decode("utf-8")
                            .split("<", 1)[0]
                            .replace("global::", "")
                            .strip()
                        )

                        base_name = (
                            qualified_base_name
                            .rsplit(".", 1)[-1]
                            .rsplit("::", 1)[-1]
                        )

                        classes.append(
                            (
                                class_name,
                                base_name,
                                qualified_base_name,
                                node.start_point.row + 1,
                            )
                        )
                        # C# allows only one direct base class. Interface
                        # implementations must not be emitted as inherits.
                        break

        for child in node.children:
            walk_classes(child)

    walk_classes(tree.root_node)

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, str, str, int]] = set()

    for class_name, base_name, qualified_base_name, line_number in classes:
        candidates = [
            symbol
            for symbol in symbol_index.find_by_name(base_name)
            if symbol.kind == "class"
        ]

        if "." in qualified_base_name or "::" in qualified_base_name:
            normalized_name = (
                qualified_base_name
                .replace("global::", "")
                .replace("::", ".")
            )
            namespace_hint = normalized_name.rsplit(".", 1)[0]

            matching_files = namespace_to_files.get(namespace_hint, set())

            candidates = [
                symbol
                for symbol in candidates
                if symbol.file_path.replace("\\", "/") in matching_files
            ]

        if len(candidates) > 1:
            candidates = [
                symbol
                for symbol in candidates
                if symbol.file_path == source_file
            ]

        if len(candidates) != 1:
            continue

        target = candidates[0]

        key = (
            source_file,
            target.file_path,
            class_name,
            target.name,
            line_number,
        )
        if key in seen:
            continue

        seen.add(key)
        dependencies.append(
            CodeDependency(
                source_file=source_file,
                target_file=target.file_path,
                kind="inherits",
                source_symbol=class_name,
                target_symbol=target.name,
                line_number=line_number,
            )
        )

    return dependencies
