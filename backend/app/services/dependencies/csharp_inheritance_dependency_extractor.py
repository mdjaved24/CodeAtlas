
import tree_sitter_c_sharp as ts_csharp
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex


CSHARP_LANGUAGE = Language(ts_csharp.language())


def extract_csharp_inheritance_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    parser = Parser(CSHARP_LANGUAGE)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    if tree.root_node.has_error:
        return []

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
                        base_name = (
                            base_node.text.decode("utf-8")
                            .split("<", 1)[0]
                            .rsplit(".", 1)[-1]
                            .rsplit("::", 1)[-1]
                        )

                        classes.append(
                            (
                                class_name,
                                base_name,
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

    for class_name, base_name, line_number in classes:
        candidates = [
            symbol
            for symbol in symbol_index.find_by_name(base_name)
            if symbol.kind == "class"
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
