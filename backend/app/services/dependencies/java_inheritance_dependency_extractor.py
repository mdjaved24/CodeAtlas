
import tree_sitter_java as ts_java
from tree_sitter import Language, Parser

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex


JAVA_LANGUAGE = Language(ts_java.language())


def extract_java_inheritance_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    parser = Parser(JAVA_LANGUAGE)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    if tree.root_node.has_error:
        return []

    package_name = ""
    imported_classes: dict[str, str] = {}

    def walk_imports(node) -> None:
        nonlocal package_name

        if node.type == "package_declaration":
            package_node = next(
                (
                    child
                    for child in node.named_children
                    if child.type == "scoped_identifier"
                    or child.type == "identifier"
                ),
                None,
            )
            if package_node is not None:
                package_name = package_node.text.decode("utf-8")

        elif node.type == "import_declaration":
            import_text = node.text.decode("utf-8").strip()
            if import_text.startswith("import static "):
                return

            qualified_name = import_text.removeprefix("import").strip().rstrip(";")

            if qualified_name.endswith(".*"):
                return

            simple_name = qualified_name.rsplit(".", 1)[-1]
            if simple_name:
                imported_classes[simple_name] = qualified_name

        for child in node.children:
            walk_imports(child)

    walk_imports(tree.root_node)

    classes: list[tuple[str, str, int]] = []

    def walk_classes(node) -> None:
        if node.type in ("class_declaration", "record_declaration"):
            name_node = node.child_by_field_name("name")
            superclass_node = node.child_by_field_name("superclass")

            if name_node is not None and superclass_node is not None:
                base_node = next(
                    iter(superclass_node.named_children),
                    None,
                )

                if base_node is not None:
                    classes.append(
                        (
                            name_node.text.decode("utf-8"),
                            base_node.text.decode("utf-8").rsplit(".", 1)[-1],
                            node.start_point.row + 1,
                        )
                    )

        for child in node.children:
            walk_classes(child)

    walk_classes(tree.root_node)

    dependencies: list[CodeDependency] = []
    seen: set[tuple[str, str, str, str, int]] = set()

    for class_name, base_name, line_number in classes:
        candidates = [
            symbol
            for symbol in symbol_index.find_by_name(base_name)
            if symbol.kind in ("class", "record")
        ]

        if base_name in imported_classes:
            qualified_import = imported_classes[base_name]
            expected_suffix = qualified_import.replace(".", "/") + ".java"

            candidates = [
                symbol
                for symbol in candidates
                if symbol.file_path.replace("\\", "/").endswith(expected_suffix)
            ]
        else:
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
