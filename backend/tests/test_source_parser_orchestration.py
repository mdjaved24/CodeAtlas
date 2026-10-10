
from pathlib import Path

from app.schemas.source_parser import ParseResult
from app.services.file_selection import FileSelection
from app.services.source_parser import parse_selected_source_files


def make_selection(
    path: str,
    language: str | None,
    selected: bool = True,
) -> FileSelection:
    """Create a file-selection manifest entry for testing."""
    return FileSelection(
        path=path,
        selected=selected,
        category="source" if language else "documentation",
        reason="Test fixture",
        language=language,
    )


def test_dispatches_python_and_javascript_files(tmp_path: Path):
    """Selected files should use their respective language parsers."""
    (tmp_path / "main.py").write_text(
        "class PaymentService:\n"
        "    def process_payment(self):\n"
        "        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "app.js").write_text(
        "function startApp() {}",
        encoding="utf-8",
    )

    manifest = [
        make_selection("main.py", "python"),
        make_selection("app.js", "javascript"),
    ]

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 2

    results_by_path = {
        result.file_path: result
        for result in results
    }

    assert results_by_path["main.py"].language == "python"
    assert results_by_path["main.py"].status == "success"
    assert {
        symbol.name
        for symbol in results_by_path["main.py"].symbols
    } == {"PaymentService", "process_payment"}

    assert results_by_path["app.js"].language == "javascript"
    assert results_by_path["app.js"].status == "success"
    assert {
        symbol.name
        for symbol in results_by_path["app.js"].symbols
    } == {"startApp"}


def test_skips_unselected_files(tmp_path: Path):
    """Files marked unselected must not be parsed."""
    (tmp_path / "included.py").write_text(
        "def run():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "excluded.py").write_text(
        "def ignored():\n    pass\n",
        encoding="utf-8",
    )

    manifest = [
        make_selection("included.py", "python", selected=True),
        make_selection("excluded.py", "python", selected=False),
    ]

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 1
    assert results[0].file_path == "included.py"


def test_skips_documentation_without_language(tmp_path: Path):
    """Selected documentation should not be sent to a source parser."""
    (tmp_path / "README.md").write_text(
        "# CodeAtlas",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "def run():\n    pass\n",
        encoding="utf-8",
    )

    manifest = [
        make_selection("README.md", None),
        make_selection("main.py", "python"),
    ]

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 1
    assert results[0].file_path == "main.py"


def test_skips_unsupported_language(tmp_path: Path):
    """An unsupported language should not crash the whole operation."""
    (tmp_path / "main.py").write_text(
        "def run():\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "unknown.xyz").write_text(
        "some source text",
        encoding="utf-8",
    )

    manifest = [
        make_selection("unknown.xyz", "brainfuck"),
        make_selection("main.py", "python"),
    ]

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 1
    assert results[0].file_path == "main.py"
    assert results[0].status == "success"


def test_missing_file_does_not_stop_other_files(tmp_path: Path):
    """A missing file should fail independently of valid files."""
    (tmp_path / "valid.py").write_text(
        "def run():\n    pass\n",
        encoding="utf-8",
    )

    manifest = [
        make_selection("missing.py", "python"),
        make_selection("valid.py", "python"),
    ]

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 2

    results_by_path = {
        result.file_path: result
        for result in results
    }

    missing_result = results_by_path["missing.py"]
    assert missing_result.status == "failed"
    assert missing_result.symbols == []
    assert any(
        "FileNotFoundError" in diagnostic
        for diagnostic in missing_result.diagnostics
    )

    valid_result = results_by_path["valid.py"]
    assert valid_result.status == "success"
    assert any(
        symbol.name == "run"
        for symbol in valid_result.symbols
    )




def test_dispatches_all_five_supported_languages(tmp_path: Path):
    sources = {
        "main.py": (
            "python",
            "def python_entry():\n    pass\n",
        ),
        "app.js": (
            "javascript",
            "function javascriptEntry() {}",
        ),
        "app.ts": (
            "typescript",
            "function typescriptEntry(): void {}",
        ),
        "Main.java": (
            "java",
            "class Main { void javaEntry() {} }",
        ),
        "Program.cs": (
            "csharp",
            "class Program { void CsharpEntry() {} }",
        ),
    }

    manifest = []

    for file_path, (language, source) in sources.items():
        (tmp_path / file_path).write_text(
            source,
            encoding="utf-8",
        )
        manifest.append(
            make_selection(file_path, language)
        )

    results = parse_selected_source_files(tmp_path, manifest)

    assert len(results) == 5

    results_by_path = {
        result.file_path: result
        for result in results
    }

    for file_path, (language, _) in sources.items():
        result = results_by_path[file_path]
        assert result.language == language
        assert result.status == "success"
        assert result.symbols
