
from pathlib import Path

from app.schemas.source_parser import CodeSymbol, ParseResult
from app.services.dependency_extractor import (
    extract_repository_dependencies,
)
from app.services.symbol_index import SymbolIndex


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
