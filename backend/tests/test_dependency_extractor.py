
from pathlib import Path

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependencies.dependency_extractor import extract_repository_dependencies
from app.services.symbols.symbol_index import SymbolIndex


def test_combines_import_and_call_dependencies(tmp_path: Path):
    (tmp_path / "users.py").write_text(
        "def validate_user():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "payment.py").write_text(
        "import users\n\n"
        "def process_payment():\n"
        "    validate_user()\n",
        encoding="utf-8",
    )

    symbols = [
        CodeSymbol(
            name="process_payment",
            kind="function",
            file_path="payment.py",
            start_line=3,
            end_line=4,
        ),
        CodeSymbol(
            name="validate_user",
            kind="function",
            file_path="users.py",
            start_line=1,
            end_line=2,
        ),
    ]

    results = [
        ParseResult(
            file_path="payment.py",
            language="python",
            status="success",
            symbols=[symbols[0]],
        ),
        ParseResult(
            file_path="users.py",
            language="python",
            status="success",
            symbols=[symbols[1]],
        ),
    ]

    dependencies = extract_repository_dependencies(
        tmp_path,
        results,
        SymbolIndex(results),
    )

    assert any(
        dependency.kind == "imports"
        and dependency.source_file == "payment.py"
        and dependency.target_file == "users.py"
        for dependency in dependencies
    )


def test_skips_failed_parse_results(tmp_path: Path):
    (tmp_path / "payment.py").write_text(
        "import users\n",
        encoding="utf-8",
    )

    result = ParseResult(
        file_path="payment.py",
        language="python",
        status="failed",
        symbols=[],
    )

    dependencies = extract_repository_dependencies(
        tmp_path,
        [result],
        SymbolIndex([result]),
    )

    assert dependencies == []


def test_skips_non_python_results(tmp_path: Path):
    (tmp_path / "payment.js").write_text(
        "import users from './users.js';\n",
        encoding="utf-8",
    )

    result = ParseResult(
        file_path="payment.js",
        language="javascript",
        status="success",
        symbols=[],
    )

    dependencies = extract_repository_dependencies(
        tmp_path,
        [result],
        SymbolIndex([result]),
    )

    assert dependencies == []


def test_skips_missing_source_file(tmp_path: Path):
    result = ParseResult(
        file_path="missing.py",
        language="python",
        status="success",
        symbols=[],
    )

    dependencies = extract_repository_dependencies(
        tmp_path,
        [result],
        SymbolIndex([result]),
    )

    assert dependencies == []





def test_extracts_javascript_import_dependencies(tmp_path):

    source_dir = tmp_path / "src"
    source_dir.mkdir()

    (source_dir / "payment.js").write_text(
        'import { validateUser } from "./users.js";\n',
        encoding="utf-8",
    )
    (source_dir / "users.js").write_text(
        "export function validateUser() {}\n",
        encoding="utf-8",
    )

    parse_results = [
        ParseResult(
            file_path="src/payment.js",
            language="javascript",
            status="success",
            symbols=[],
        ),
        ParseResult(
            file_path="src/users.js",
            language="javascript",
            status="success",
            symbols=[],
        ),
    ]

    dependencies = extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/payment.js"
    assert dependencies[0].target_file == "src/users.js"
    assert dependencies[0].kind == "imports"




def test_extracts_typescript_import_dependencies(tmp_path):
    from app.services.dependencies.dependency_extractor import (
        extract_repository_dependencies,
    )
    from app.schemas.source_parser import ParseResult
    from app.services.symbols.symbol_index import SymbolIndex

    source_dir = tmp_path / "src"
    source_dir.mkdir()

    (source_dir / "payment.ts").write_text(
        'import { validateUser } from "./users";\n',
        encoding="utf-8",
    )
    (source_dir / "users.ts").write_text(
        "export function validateUser(): void {}\n",
        encoding="utf-8",
    )

    parse_results = [
        ParseResult(
            file_path="src/payment.ts",
            language="typescript",
            status="success",
            symbols=[],
        ),
        ParseResult(
            file_path="src/users.ts",
            language="typescript",
            status="success",
            symbols=[],
        ),
    ]

    dependencies = extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/payment.ts"
    assert dependencies[0].target_file == "src/users.ts"
    assert dependencies[0].kind == "imports"




def test_extracts_java_import_dependencies(tmp_path):
    from app.schemas.source_parser import ParseResult
    from app.services.dependencies.dependency_extractor import (
        extract_repository_dependencies,
    )
    from app.services.symbols.symbol_index import SymbolIndex

    source_dir = tmp_path / "src/main/java/com/example"
    source_dir.mkdir(parents=True)

    (source_dir / "PaymentService.java").write_text(
        """\
package com.example;

import com.example.users.UserService;

public class PaymentService {}
""",
        encoding="utf-8",
    )

    users_dir = source_dir / "users"
    users_dir.mkdir()

    (users_dir / "UserService.java").write_text(
        """\
package com.example.users;

public class UserService {}
""",
        encoding="utf-8",
    )

    parse_results = [
        ParseResult(
            file_path="src/main/java/com/example/PaymentService.java",
            language="java",
            status="success",
            symbols=[],
        ),
        ParseResult(
            file_path="src/main/java/com/example/users/UserService.java",
            language="java",
            status="success",
            symbols=[],
        ),
    ]

    dependencies = extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == (
        "src/main/java/com/example/PaymentService.java"
    )
    assert dependencies[0].target_file == (
        "src/main/java/com/example/users/UserService.java"
    )
    assert dependencies[0].kind == "imports"
    assert dependencies[0].line_number == 3



def test_extracts_csharp_import_dependencies(tmp_path):
    from app.schemas.source_parser import ParseResult
    from app.services.dependencies.dependency_extractor import (
        extract_repository_dependencies,
    )
    from app.services.symbols.symbol_index import SymbolIndex

    services_dir = tmp_path / "Services"
    services_dir.mkdir(parents=True)

    (services_dir / "UserService.cs").write_text(
        """\
namespace MyApp.Services
{
    public class UserService {}
}
""",
        encoding="utf-8",
    )

    controllers_dir = tmp_path / "Controllers"
    controllers_dir.mkdir(parents=True)

    (controllers_dir / "UserController.cs").write_text(
        """\
using MyApp.Services;

namespace MyApp.Controllers
{
    public class UserController {}
}
""",
        encoding="utf-8",
    )

    parse_results = [
        ParseResult(
            file_path="Controllers/UserController.cs",
            language="csharp",
            status="success",
            symbols=[],
        ),
        ParseResult(
            file_path="Services/UserService.cs",
            language="csharp",
            status="success",
            symbols=[],
        ),
    ]

    dependencies = extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == (
        "Controllers/UserController.cs"
    )
    assert dependencies[0].target_file == "Services/UserService.cs"
    assert dependencies[0].kind == "imports"
    assert dependencies[0].line_number == 1




def test_records_diagnostic_when_import_extractor_fails(
    tmp_path, monkeypatch, caplog
):
    import logging

    from app.schemas.source_parser import ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    source_file = tmp_path / "example.py"
    source_file.write_text(
        "import os\n",
        encoding="utf-8",
    )

    def failing_extractor(**kwargs):
        raise RuntimeError("simulated extractor failure")

    monkeypatch.setattr(
        extractor_module,
        "extract_python_import_dependencies",
        failing_extractor,
    )

    parse_results = [
        ParseResult(
            file_path="example.py",
            language="python",
            status="success",
            symbols=[],
        )
    ]

    with caplog.at_level(
        logging.ERROR,
        logger=extractor_module.__name__,
    ):
        dependencies = extractor_module.extract_repository_dependencies(
            repository_root=tmp_path,
            parse_results=parse_results,
            symbol_index=SymbolIndex([]),
        )

    assert dependencies == []
    
    assert any(
        "Dependency extraction failed for example.py in python"
        in record.message
        and record.exc_info is not None
        and "simulated extractor failure" in str(record.exc_info[1])
        for record in caplog.records
    )





def test_orchestrator_deduplicates_identical_dependencies(
    tmp_path, monkeypatch
):
    from app.schemas.dependency import CodeDependency
    from app.schemas.source_parser import ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    source_file = tmp_path / "example.py"
    source_file.write_text("import os\n", encoding="utf-8")

    dependency = CodeDependency(
        source_file="example.py",
        target_file="utils.py",
        kind="imports",
        line_number=1,
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_python_import_dependencies",
        lambda **kwargs: [dependency, dependency.model_copy()],
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_python_call_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="example.py",
            language="python",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert dependencies == [dependency]




def test_orchestrator_returns_stable_dependency_order(
    tmp_path, monkeypatch
):
    from app.schemas.dependency import CodeDependency
    from app.schemas.source_parser import ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "example.py").write_text(
        "import os\n",
        encoding="utf-8",
    )

    first = CodeDependency(
        source_file="example.py",
        target_file="zebra.py",
        kind="imports",
        line_number=1,
    )
    second = CodeDependency(
        source_file="example.py",
        target_file="alpha.py",
        kind="imports",
        line_number=2,
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_python_import_dependencies",
        lambda **kwargs: [first, second],
    )
    monkeypatch.setattr(
        extractor_module,
        "extract_python_call_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="example.py",
            language="python",
            status="success",
            symbols=[],
        )
    ]

    def run_extraction():
        return extractor_module.extract_repository_dependencies(
            repository_root=tmp_path,
            parse_results=parse_results,
            symbol_index=SymbolIndex([]),
        )

    first_run = run_extraction()
    second_run = run_extraction()

    assert first_run == [first, second]
    assert second_run == first_run




def test_orchestrator_processes_all_five_languages(
    tmp_path, monkeypatch
):
    from app.schemas.dependency import CodeDependency
    from app.schemas.source_parser import ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    languages = {
        "python": "example.py",
        "javascript": "example.js",
        "typescript": "example.ts",
        "java": "Example.java",
        "csharp": "Example.cs",
    }

    for file_path in languages.values():
        (tmp_path / file_path).write_text(
            "// test source\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extractor_module,
        "extract_python_import_dependencies",
        lambda **kwargs: [
            CodeDependency(
                source_file=kwargs["source_file"],
                target_file="python_target.py",
                kind="imports",
                line_number=1,
            )
        ],
    )
    monkeypatch.setattr(
        extractor_module,
        "extract_python_call_dependencies",
        lambda **kwargs: [],
    )

    extractor_names = {
        "javascript": "extract_javascript_import_dependencies",
        "typescript": "extract_typescript_import_dependencies",
        "java": "extract_java_import_dependencies",
        "csharp": "extract_csharp_import_dependencies",
    }

    for language, extractor_name in extractor_names.items():
        monkeypatch.setattr(
            extractor_module,
            extractor_name,
            lambda language=language, **kwargs: [
                CodeDependency(
                    source_file=kwargs["source_file"],
                    target_file=f"{language}_target.cs",
                    kind="imports",
                    line_number=1,
                )
            ],
        )

    parse_results = [
        ParseResult(
            file_path=file_path,
            language=language,
            status="success",
            symbols=[],
        )
        for language, file_path in languages.items()
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=SymbolIndex([]),
    )

    assert len(dependencies) == 5
    assert {dependency.source_file for dependency in dependencies} == set(
        languages.values()
    )




def test_orchestrator_extracts_python_inheritance(tmp_path, monkeypatch):
    from app.schemas.source_parser import CodeSymbol, ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "animals.py").write_text(
        "class Animal:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "dogs.py").write_text(
        "from animals import Animal\n\nclass Dog(Animal):\n    pass\n",
        encoding="utf-8",
    )

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

    monkeypatch.setattr(
        extractor_module,
        "extract_python_import_dependencies",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        extractor_module,
        "extract_python_call_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="dogs.py",
            language="python",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=symbol_index,
    )

    inheritance_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.kind == "inherits"
    ]

    assert len(inheritance_dependencies) == 1
    assert inheritance_dependencies[0].source_file == "dogs.py"
    assert inheritance_dependencies[0].target_file == "animals.py"
    assert inheritance_dependencies[0].source_symbol == "Dog"
    assert inheritance_dependencies[0].target_symbol == "Animal"




def test_orchestrator_extracts_javascript_inheritance(
    tmp_path, monkeypatch
):
    from app.schemas.source_parser import CodeSymbol, ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "Animal.js").write_text(
        "class Animal {}\n",
        encoding="utf-8",
    )
    (tmp_path / "Dog.js").write_text(
        'import { Animal } from "./Animal.js";\n'
        "class Dog extends Animal {}\n",
        encoding="utf-8",
    )

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
            )
        ]
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_javascript_import_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="Dog.js",
            language="javascript",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=symbol_index,
    )

    inheritance_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.kind == "inherits"
    ]

    assert len(inheritance_dependencies) == 1
    assert inheritance_dependencies[0].source_file == "Dog.js"
    assert inheritance_dependencies[0].target_file == "Animal.js"
    assert inheritance_dependencies[0].source_symbol == "Dog"
    assert inheritance_dependencies[0].target_symbol == "Animal"




def test_orchestrator_extracts_typescript_inheritance(
    tmp_path, monkeypatch
):
    from app.schemas.source_parser import CodeSymbol, ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "Animal.ts").write_text(
        "export class Animal {}\n",
        encoding="utf-8",
    )
    (tmp_path / "Dog.ts").write_text(
        'import { Animal } from "./Animal";\n'
        "class Dog extends Animal {}\n",
        encoding="utf-8",
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
                    )
                ],
            )
        ]
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_typescript_import_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="Dog.ts",
            language="typescript",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=symbol_index,
    )

    inheritance_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.kind == "inherits"
    ]

    assert len(inheritance_dependencies) == 1
    assert inheritance_dependencies[0].source_file == "Dog.ts"
    assert inheritance_dependencies[0].target_file == "Animal.ts"
    assert inheritance_dependencies[0].source_symbol == "Dog"
    assert inheritance_dependencies[0].target_symbol == "Animal"



def test_orchestrator_extracts_java_inheritance(tmp_path, monkeypatch):
    from app.schemas.source_parser import CodeSymbol, ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "Dog.java").write_text(
        "class Animal {}\n"
        "class Dog extends Animal {}\n",
        encoding="utf-8",
    )

    symbol_index = SymbolIndex(
        [
            ParseResult(
                file_path="Dog.java",
                language="java",
                status="success",
                symbols=[
                    CodeSymbol(
                        name="Animal",
                        kind="class",
                        file_path="Dog.java",
                        start_line=1,
                        end_line=1,
                    ),
                    CodeSymbol(
                        name="Dog",
                        kind="class",
                        file_path="Dog.java",
                        start_line=2,
                        end_line=2,
                    ),
                ],
            )
        ]
    )

    monkeypatch.setattr(
        extractor_module,
        "extract_java_import_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="Dog.java",
            language="java",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=symbol_index,
    )

    inheritance_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.kind == "inherits"
    ]

    assert len(inheritance_dependencies) == 1
    assert inheritance_dependencies[0].source_file == "Dog.java"
    assert inheritance_dependencies[0].target_file == "Dog.java"
    assert inheritance_dependencies[0].source_symbol == "Dog"
    assert inheritance_dependencies[0].target_symbol == "Animal"
    assert inheritance_dependencies[0].line_number == 2



def test_orchestrator_extracts_csharp_inheritance(tmp_path, monkeypatch):
    from app.schemas.source_parser import CodeSymbol, ParseResult
    import app.services.dependencies.dependency_extractor as extractor_module
    from app.services.symbols.symbol_index import SymbolIndex

    (tmp_path / "Animal.cs").write_text(
        "class Animal {}\n",
        encoding="utf-8",
    )
    (tmp_path / "Dog.cs").write_text(
        "class Dog : Animal {}\n",
        encoding="utf-8",
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

    monkeypatch.setattr(
        extractor_module,
        "extract_csharp_import_dependencies",
        lambda **kwargs: [],
    )

    parse_results = [
        ParseResult(
            file_path="Dog.cs",
            language="csharp",
            status="success",
            symbols=[],
        )
    ]

    dependencies = extractor_module.extract_repository_dependencies(
        repository_root=tmp_path,
        parse_results=parse_results,
        symbol_index=symbol_index,
    )

    inheritance_dependencies = [
        dependency
        for dependency in dependencies
        if dependency.kind == "inherits"
    ]

    assert len(inheritance_dependencies) == 1
    assert inheritance_dependencies[0].source_file == "Dog.cs"
    assert inheritance_dependencies[0].target_file == "Animal.cs"
    assert inheritance_dependencies[0].source_symbol == "Dog"
    assert inheritance_dependencies[0].target_symbol == "Animal"
