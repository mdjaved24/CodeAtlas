
import pytest

from app.services.file_selection import (
    select_file,
    select_files,
)


@pytest.mark.parametrize(
    ("path", "language"),
    [
        ("src/main.py", "python"),
        ("src/app.js", "javascript"),
        ("src/App.tsx", "typescript"),
        ("src/Main.java", "java"),
        ("src/Program.cs", "csharp"),
    ],
)
def test_selects_supported_source_languages(path, language):
    result = select_file(path)

    assert result.selected is True
    assert result.category == "source"
    assert result.language == language


def test_selects_test_source_separately():
    result = select_file("tests/test_parser.py")

    assert result.selected is True
    assert result.category == "test"
    assert result.language == "python"


@pytest.mark.parametrize(
    "path",
    [
        "node_modules/example/index.js",
        ".git/config",
        "src/__pycache__/main.py",
        "dist/bundle.js",
    ],
)
def test_excludes_dependency_metadata_and_build_directories(path):
    result = select_file(path)

    assert result.selected is False
    assert result.category == "excluded_directory"


@pytest.mark.parametrize(
    "path",
    [
        "src/app.min.js",
        "src/app.js.map",
        "src/Program.g.cs",
        "assets/logo.png",
        "bin/application.dll",
    ],
)
def test_excludes_generated_and_binary_files(path):
    result = select_file(path)

    assert result.selected is False


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "credentials.json",
        "certs/server.pem",
        "keys/private.key",
    ],
)
def test_mandatory_sensitive_file_exclusions(path):
    result = select_file(path, include_patterns=["**/*"])

    assert result.selected is False
    assert result.category == "sensitive_file"


def test_selects_documentation_and_configuration():
    readme = select_file("README.md")
    docs = select_file("docs/design.md")
    config = select_file("pyproject.toml")

    assert readme.category == "documentation"
    assert readme.selected is True

    assert docs.category == "documentation"
    assert docs.selected is True

    assert config.category == "configuration"
    assert config.selected is True


def test_include_pattern_can_select_otherwise_unsupported_text_path():
    result = select_file(
        "notes/analysis.rst",
        include_patterns=["notes/*.rst"],
    )

    assert result.selected is True
    assert result.category == "user_included"


def test_user_exclusion_pattern_excludes_supported_source():
    result = select_file(
        "src/experimental.py",
        exclude_patterns=["src/experimental.py"],
    )

    assert result.selected is False
    assert result.category == "user_excluded"


@pytest.mark.parametrize(
    "path",
    [
        "../outside.py",
        "/absolute/path.py",
        r"src\main.py",
        "C:/outside.py",
    ],
)
def test_rejects_unsafe_paths(path):
    result = select_file(path, include_patterns=["**/*"])

    assert result.selected is False
    assert result.category == "unsafe_path"


def test_file_selection_order_is_deterministic():
    paths = [
        "src/z.py",
        "README.md",
        "src/a.ts",
    ]

    first = select_files(paths)
    second = select_files(paths)

    assert first == second
    assert [item.path for item in first] == sorted(paths)
