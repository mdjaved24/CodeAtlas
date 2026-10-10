
from pathlib import Path

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.inheritance_dependency_extractor import (
    extract_python_inheritance_dependencies,
)
from app.services.symbols.symbol_index import SymbolIndex


def test_resolves_python_class_inheritance(tmp_path: Path) -> None:
    base_file = tmp_path / "animals.py"
    base_file.write_text(
        "class Animal:\n    pass\n",
        encoding="utf-8",
    )

    source = """\
from animals import Animal

class Dog(Animal):
    pass
"""

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="animals.py",
                language="python",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="animals.py",
                        start_line=1,
                        end_line=2,
                    )
                ],
            )
        ]
    )

    dependencies = extract_python_inheritance_dependencies(
        source_file="dogs.py",
        source_code=source,
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "dogs.py"
    assert dependencies[0].target_file == "animals.py"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"


def test_ignores_unresolved_python_base_class() -> None:
    source = """\
class Dog(UnknownAnimal):
    pass
"""

    dependencies = extract_python_inheritance_dependencies(
        source_file="dogs.py",
        source_code=source,
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []


def test_ignores_ambiguous_python_base_class() -> None:
    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="animals.py",
                language="python",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="animals.py",
                        start_line=1,
                        end_line=2,
                    )
                ],
            ),
            ParseResult(
                file_path="pets.py",
                language="python",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="pets.py",
                        start_line=1,
                        end_line=2,
                    )
                ],
            ),
        ]
    )

    dependencies = extract_python_inheritance_dependencies(
        source_file="dogs.py",
        source_code="class Dog(Animal):\n    pass\n",
        symbol_index=symbol_index,
    )

    assert dependencies == []


def test_ignores_invalid_python_syntax() -> None:
    dependencies = extract_python_inheritance_dependencies(
        source_file="dogs.py",
        source_code="class Dog(Animal\n",
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == []



def test_resolves_same_file_python_inheritance() -> None:
    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="animals.py",
                language="python",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="animals.py",
                        start_line=1,
                        end_line=2,
                    )
                ],
            )
        ]
    )

    dependencies = extract_python_inheritance_dependencies(
        source_file="animals.py",
        source_code=(
            "class Animal:\n"
            "    pass\n\n"
            "class Dog(Animal):\n"
            "    pass\n"
        ),
        symbol_index=symbol_index,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "animals.py"
    assert dependencies[0].target_file == "animals.py"
    assert dependencies[0].source_symbol == "Dog"
    assert dependencies[0].target_symbol == "Animal"
    assert dependencies[0].kind == "inherits"
    assert dependencies[0].line_number == 4