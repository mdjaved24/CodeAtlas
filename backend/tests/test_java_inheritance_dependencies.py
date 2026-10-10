
from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.java_inheritance_dependency_extractor import (
    extract_java_inheritance_dependencies,
)
from app.services.symbols.symbol_index import SymbolIndex


def test_resolves_java_class_inheritance(tmp_path):
    target_file = tmp_path / "Animal.java"
    target_file.write_text(
        "package com.animals;\n"
        "public class Animal {}\n",
        encoding="utf-8",
    )

    source_code = (
        "package com.pets;\n"
        "import com.animals.Animal;\n"
        "public class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="src/main/java/com/animals/Animal.java",
                language="java",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/main/java/com/animals/Animal.java",
                        start_line=2,
                        end_line=2,
                    )
                ],
            )
        ]
    )

    dependencies = extract_java_inheritance_dependencies(
        source_file="src/main/java/com/pets/Dog.java",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/main/java/com/pets/Dog.java"
    assert dependencies[0].target_file == "src/main/java/com/animals/Animal.java"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].line_number == 3


def test_ignores_unresolved_java_base_class():
    source_code = (
        "package com.pets;\n"
        "public class Dog extends UnknownAnimal {}\n"
    )

    dependencies = extract_java_inheritance_dependencies(
        source_file="src/main/java/com/pets/Dog.java",
        source_code=source_code,
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []


def test_resolves_same_file_java_inheritance():
    source_code = (
        "class Animal {}\n"
        "class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Animal.java",
                language="java",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Animal.java",
                        start_line=1,
                        end_line=1,
                    ),
                    CodeSymbol(
                        name="Dog",
                        kind="class",
                        file_path="Animal.java",
                        start_line=2,
                        end_line=2,
                    ),
                ],
            )
        ]
    )

    dependencies = extract_java_inheritance_dependencies(
        source_file="Animal.java",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Animal.java"
    assert dependencies[0].target_file == "Animal.java"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].line_number == 2




def test_resolves_imported_base_class_when_duplicate_names_exist():
    source_code = (
        "package com.pets;\n"
        "import com.animals.Animal;\n"
        "class Dog extends Animal {}\n"
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="src/main/java/com/animals/Animal.java",
                language="java",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/main/java/com/animals/Animal.java",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
            ParseResult(
                file_path="src/main/java/com/pets/Animal.java",
                language="java",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="src/main/java/com/pets/Animal.java",
                        start_line=1,
                        end_line=1,
                    )
                ],
            ),
        ]
    )

    dependencies = extract_java_inheritance_dependencies(
        source_file="src/main/java/com/pets/Dog.java",
        source_code=source_code,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].kind == "inherits"
    assert (
        dependencies[0].target_file
        == "src/main/java/com/animals/Animal.java"
    )
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
