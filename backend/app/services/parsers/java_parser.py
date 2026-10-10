import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

from app.schemas.source_parser import CodeSymbol, ParseResult


def create_java_parser() -> Parser:
    """Create a parser using the Java grammar."""
    return Parser(Language(tsjava.language()))


def parse_java_source(
    source: str,
    file_path: str,
) -> ParseResult:
    """Extract classes and methods from Java source."""

    if not file_path.strip():
        raise ValueError("file_path must not be empty")

    source_bytes = source.encode("utf-8")
    tree = create_java_parser().parse(source_bytes)
    root = tree.root_node

    symbols: list[CodeSymbol] = []
    diagnostics: list[str] = []

    def text_of(node) -> str:
        return source_bytes[
            node.start_byte:node.end_byte
        ].decode("utf-8")

    def visit(node, parent_class: str | None = None) -> None:
        if node.type in {
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        }:
            name_node = node.child_by_field_name("name")

            if name_node is not None:
                class_name = text_of(name_node)

                symbols.append(
                    CodeSymbol(
                        name=class_name,
                        kind="class",
                        file_path=file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        parent_name=parent_class,
                    )
                )

                for child in node.named_children:
                    visit(child, class_name)

                return

        if node.type == "method_declaration":
            name_node = node.child_by_field_name("name")

            if name_node is not None:
                symbols.append(
                    CodeSymbol(
                        name=text_of(name_node),
                        kind="method",
                        file_path=file_path,
                        start_line=node.start_point.row + 1,
                        end_line=node.end_point.row + 1,
                        parent_name=parent_class,
                    )
                )

                for child in node.named_children:
                    visit(child, parent_class)

                return

        for child in node.named_children:
            visit(child, parent_class)

    visit(root)

    has_errors = root.has_error

    if has_errors:
        diagnostics.append(
            "Tree-sitter detected syntax errors or missing syntax "
            "in the source file."
        )

    return ParseResult(
        file_path=file_path,
        language="java",
        status="partial" if has_errors else "success",
        symbols=symbols,
        has_syntax_errors=has_errors,
        diagnostics=diagnostics,
    )