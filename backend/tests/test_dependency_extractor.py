
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
