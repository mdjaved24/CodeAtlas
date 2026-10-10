
import tree_sitter_javascript as ts_javascript
from tree_sitter import Language, Parser
from pathlib import PurePosixPath
import posixpath

from app.schemas.dependency import CodeDependency
from app.services.symbols.symbol_index import SymbolIndex


JAVASCRIPT_LANGUAGE = Language(ts_javascript.language())



def _resolve_imported_module(
    source_file: str,
    module_path: str,
    symbol_index: SymbolIndex,
) -> set[str]:
    """Resolve a relative JavaScript import to indexed repository files."""
    if not module_path.startswith("."):
        return set()

    source_directory = posixpath.dirname(source_file.replace("\\", "/"))
    resolved_path = posixpath.normpath(
        posixpath.join(source_directory, module_path)
    )

    extensions = ("", ".js", ".jsx", ".mjs", ".cjs")
    candidates: set[str] = set()

    for extension in extensions:
        candidates.add(resolved_path + extension)

    for extension in (".js", ".jsx", ".mjs", ".cjs"):
        candidates.add(posixpath.join(resolved_path, "index" + extension))

    indexed_files = {
        symbol.file_path.replace("\\", "/")
        for symbol in symbol_index.all_symbols()
    }

    return candidates & indexed_files


def extract_javascript_inheritance_dependencies(
    source_file: str,
    source_code: str,
    symbol_index: SymbolIndex,
) -> list[CodeDependency]:
    """Extract confidently resolved JavaScript class inheritance edges."""
    parser = Parser(JAVASCRIPT_LANGUAGE)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    if tree.root_node.has_error:
        return []

    # Record explicitly imported names and their source modules.
    imported_names: dict[str, str] = {}

    def walk_imports(node) -> None:
        if node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            if source_node is not None:
                module_path = source_node.text.decode("utf-8").strip("'\"")

                for child in node.children:
                    if child.type == "import_clause":
                        for imported in child.children:
                            if imported.type == "identifier":
                                name = imported.text.decode("utf-8")
                                imported_names[name] = module_path
                            elif imported.type == "named_imports":
                                for specifier in imported.named_children:
                                    if specifier.type == "import_specifier":
                                        name_node = (
                                            specifier.child_by_field_name("name")
                                        )
                                        alias_node = (
                                            specifier.child_by_field_name("alias")
                                        )
                                        if name_node is None:
                                            continue

                                        imported_name = name_node.text.decode("utf-8")
                                        local_name = (
                                            alias_node.text.decode("utf-8")
                                            if alias_node is not None
                                            else imported_name
                                        )
                                        imported_names[local_name] = module_path

        for child in node.children:
            walk_imports(child)

    walk_imports(tree.root_node)

    # Collect local class declarations and their base-class names.
    classes: list[tuple[str, str, int]] = []

    def walk_classes(node) -> None:
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            heritage_node = next(
                (
                    child
                    for child in node.named_children
                    if child.type == "class_heritage"
                ),
                None,
            )

            if name_node is not None and heritage_node is not None:
                name = name_node.text.decode("utf-8")
                for child in heritage_node.named_children:
                    if child.type == "identifier":
                        classes.append(
                            (name, child.text.decode("utf-8"), node.start_point.row + 1)
                        )
                    elif child.type == "member_expression":
                        property_node = child.child_by_field_name("property")
                        if property_node is not None:
                            classes.append(
                                (
                                    name,
                                    property_node.text.decode("utf-8"),
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
            if symbol.kind == "class"
        ]

        if base_name in imported_names:
            module_path = imported_names[base_name]
            resolved_files = _resolve_imported_module(
                source_file=source_file,
                module_path=module_path,
                symbol_index=symbol_index,
            )

            candidates = [
                symbol
                for symbol in candidates
                if symbol.file_path.replace("\\", "/") in resolved_files
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
