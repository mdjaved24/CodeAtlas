from pathlib import Path, PurePosixPath

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.file_selection import FileSelection



def create_python_parser() -> Parser:
    language = Language(tspython.language())
    return Parser(language)



def parse_python_source(
    source: str,
    file_path: str,
) -> ParseResult:
    """Extract classes, functions, and methods from Python source."""

    if not file_path.strip():
        raise ValueError("file_path must not be empty")

    parser = create_python_parser()
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)
    root = tree.root_node

    symbols: list[CodeSymbol] = []
    diagnostics: list[str] = []

    
    def visit(
        node,
        parent_class: str | None = None,
        parent_function: str | None = None,
    ) -> None:
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")

            if name_node is not None:
                class_name = source_bytes[
                    name_node.start_byte:name_node.end_byte
                ].decode("utf-8")

                symbols.append(
                    CodeSymbol(
                        name=class_name,
                        kind="class",
                        file_path=file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        parent_name=parent_function or parent_class,
                    )
                )

                for child in node.named_children:
                    visit(child, class_name, None)

                return

        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")

            if name_node is not None:
                function_name = source_bytes[
                    name_node.start_byte:name_node.end_byte
                ].decode("utf-8")

                is_method = (
                    parent_class is not None
                    and parent_function is None
                )

                symbols.append(
                    CodeSymbol(
                        name=function_name,
                        kind="method" if is_method else "function",
                        file_path=file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        parent_name=parent_function or parent_class,
                    )
                )

                for child in node.named_children:
                    visit(child, parent_class, function_name)

                return

        for child in node.named_children:
            visit(child, parent_class, parent_function)

    visit(root)


    has_errors = root.has_error

    if has_errors:
        diagnostics.append(
            "Tree-sitter detected syntax errors or missing syntax "
            "in the source file."
        )

    return ParseResult(
        file_path=file_path,
        language="python",
        status="partial" if has_errors else "success",
        symbols=symbols,
        has_syntax_errors=has_errors,
        diagnostics=diagnostics,
    )



