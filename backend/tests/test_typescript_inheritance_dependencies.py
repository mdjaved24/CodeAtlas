
from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.typescript_inheritance_dependency_extractor import (
    extract_typescript_inheritance_dependencies,
)
from app.services.symbols.symbol_index import SymbolIndex


def create_symbol_index(name: str, file_path: str) -> SymbolIndex:
    return SymbolIndex(
        [
            ParseResult(
                file_path=file_path,
                language="typescript",
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


def test_resolves_typescript_class_inheritance(tmp_path):
    target_file = tmp_path / "Animal.ts"
    target_file.write_text(
        "export class Animal {}\n",
        encoding="utf-8",
    )

    source_code = (
        'import { Animal } from "./Animal";\n'
        "class Dog extends Animal {}\n"
    )

    dependencies = extract_typescript_inheritance_dependencies(
        source_file="Dog.ts",
        source_code=source_code,
        symbol_index=create_symbol_index("Animal", "Animal.ts"),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Dog.ts"
    assert dependencies[0].target_file == "Animal.ts"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].line_number == 2


def test_ignores_unresolved_typescript_base_class():
    source_code = "class Dog extends UnknownAnimal {}\n"

    dependencies = extract_typescript_inheritance_dependencies(
        source_file="Dog.ts",
        source_code=source_code,
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []


def test_resolves_same_file_typescript_inheritance():
    source_code = (
        "class Animal {}\n"
        "class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Animal.ts",
                language="typescript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Animal.ts",
                        start_line=1,
                        end_line=1,
                    ),
                    CodeSymbol(
                        name="Dog",
                        kind="class",
                        file_path="Animal.ts",
                        start_line=2,
                        end_line=2,
                    ),
                ],
            )
        ]
    )

    dependencies = extract_typescript_inheritance_dependencies(
        source_file="Animal.ts",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].source_file == "Animal.ts"
    assert dependencies[0].target_file == "Animal.ts"




def test_resolves_imported_base_class_when_duplicate_names_exist():
    source_code = (
        'import { Animal } from "./Animal";\n'
        "class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="src/Animal.ts",
                language="typescript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/Animal.ts",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
            ParseResult(
                file_path="src/Pet.ts",
                language="typescript",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/Pet.ts",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
        ]
    )

    dependencies = extract_typescript_inheritance_dependencies(
        source_file="src/Dog.ts",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_file == "src/Dog.ts"
    assert dependencies[0].target_file == "src/Animal.ts"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
