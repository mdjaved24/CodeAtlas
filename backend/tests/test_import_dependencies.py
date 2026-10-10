
from pathlib import Path

from app.services.dependencies.import_dependency_extractor import (
    extract_python_import_dependencies,
)


def test_extracts_absolute_import(tmp_path: Path):
    (tmp_path / "services").mkdir()
    (tmp_path / "services" / "user.py").write_text(
        "class UserService:\n    pass\n",
        encoding="utf-8",
    )

    dependencies = extract_python_import_dependencies(
        tmp_path,
        "payment.py",
        "from services.user import UserService\n",
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "payment.py"
    assert dependencies[0].target_file == "services/user.py"
    assert dependencies[0].kind == "imports"
    assert dependencies[0].line_number == 1


def test_extracts_relative_import(tmp_path: Path):
    services = tmp_path / "services"
    services.mkdir()
    (services / "user.py").write_text(
        "class UserService:\n    pass\n",
        encoding="utf-8",
    )

    dependencies = extract_python_import_dependencies(
        tmp_path,
        "services/payment.py",
        "from .user import UserService\n",
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "services/user.py"


def test_ignores_external_import(tmp_path: Path):
    dependencies = extract_python_import_dependencies(
        tmp_path,
        "main.py",
        "import requests\n",
    )

    assert dependencies == []


def test_ignores_syntax_errors(tmp_path: Path):
    dependencies = extract_python_import_dependencies(
        tmp_path,
        "main.py",
        "from services.user import\n",
    )

    assert dependencies == []


def test_does_not_duplicate_same_line_dependency(tmp_path: Path):
    (tmp_path / "user.py").write_text(
        "class UserService:\n    pass\n",
        encoding="utf-8",
    )

    dependencies = extract_python_import_dependencies(
        tmp_path,
        "main.py",
        "import user\nimport user\n",
    )

    assert len(dependencies) == 2
    assert all(item.target_file == "user.py" for item in dependencies)
