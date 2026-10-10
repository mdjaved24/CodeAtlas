
from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.csharp_inheritance_dependency_extractor import (
    extract_csharp_inheritance_dependencies,
)
from app.services.symbols.symbol_index import SymbolIndex


def test_resolves_csharp_class_inheritance():
    source_code = (
        "namespace Pets;\n"
        "public class Dog : Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Animal.cs",
                language="csharp",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Animal.cs",
                        start_line=1,
                        end_line=1,
                    )
                ],
            )
        ]
    )

    dependencies = extract_csharp_inheritance_dependencies(
        source_file="Dog.cs",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Dog.cs"
    assert dependencies[0].target_file == "Animal.cs"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].line_number == 2


def test_ignores_unresolved_csharp_base_class():
    source_code = "public class Dog : UnknownAnimal {}\n"

    dependencies = extract_csharp_inheritance_dependencies(
        source_file="Dog.cs",
        source_code=source_code,
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []


def test_resolves_same_file_csharp_inheritance():
    source_code = (
        "class Animal {}\n"
        "class Dog : Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Animal.cs",
                language="csharp",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Animal.cs",
                        start_line=1,
                        end_line=1,
                    ),
                    CodeSymbol(
                        name="Dog",
                        kind="class",
                        file_path="Animal.cs",
                        start_line=2,
                        end_line=2,
                    ),
                ],
            )
        ]
    )

    dependencies = extract_csharp_inheritance_dependencies(
        source_file="Animal.cs",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Animal.cs"
    assert dependencies[0].target_file == "Animal.cs"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].line_number == 2
