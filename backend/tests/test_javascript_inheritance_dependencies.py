
from pathlib import Path

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.javascript_inheritance_dependency_extractor import (
    extract_javascript_inheritance_dependencies,
)
from app.services.symbols.symbol_index import SymbolIndex


def create_symbol_index(
    name: str,
    file_path: str,
) -> SymbolIndex:
    return SymbolIndex(
        [
            ParseResult(
                file_path=file_path,
                language="javascript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name=name,
                        kind="class",
                        file_path=file_path,
                        start_line=1,
                        end_line=3,
                    )
                ],
            )
        ]
    )


def test_resolves_javascript_class_inheritance(tmp_path: Path) -> None:
    base_file = tmp_path / "Animal.js"
    base_file.write_text(
        "class Animal {}\n",
        encoding="utf-8",
    )

    source = """\
import { Animal } from "./Animal.js";

class Dog extends Animal {}
"""

    dependencies = extract_javascript_inheritance_dependencies(
        source_file="Dog.js",
        source_code=source,
        symbol_index=create_symbol_index("Animal", "Animal.js"),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Dog.js"
    assert dependencies[0].target_file == "Animal.js"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"


def test_ignores_unresolved_javascript_base_class() -> None:
    dependencies = extract_javascript_inheritance_dependencies(
        source_file="Dog.js",
        source_code="class Dog extends UnknownAnimal {}\n",
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []


def test_resolves_same_file_javascript_inheritance() -> None:
    symbol_index = create_symbol_index("Animal", "Animal.js")

    source = """\
class Animal {}

class Dog extends Animal {}
"""

    dependencies = extract_javascript_inheritance_dependencies(
        source_file="Animal.js",
        source_code=source,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Animal.js"
    assert dependencies[0].target_file == "Animal.js"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].kind == "inherits"


def test_ignores_ambiguous_javascript_base_class() -> None:
    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Animal.js",
                language="javascript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Animal.js",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
            ParseResult(
                file_path="Pet.js",
                language="javascript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Pet.js",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
        ]
    )

    source = """\
class Dog extends Animal {}
"""

    dependencies = extract_javascript_inheritance_dependencies(
        source_file="Dog.js",
        source_code=source,
        symbol_index=symbol_index,
    )

    assert dependencies == []


def test_ignores_malformed_javascript() -> None:
    dependencies = extract_javascript_inheritance_dependencies(
        source_file="Dog.js",
        source_code="class Dog extends {\n",
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []



def test_resolves_imported_base_class_when_duplicate_names_exist():
    source_code = (
        'import { Animal } from "./Animal.js";\n'
        "class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="src/Animal.js",
                language="javascript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/Animal.js",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
            ParseResult(
                file_path="src/Pet.js",
                language="javascript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/Pet.js",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
        ]
    )

    dependencies = extract_javascript_inheritance_dependencies(
        source_file="src/Dog.js",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_file == "src/Dog.js"
    assert dependencies[0].target_file == "src/Animal.js"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
