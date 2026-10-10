
from pathlib import Path

from app.services.dependencies.javascript_import_dependency_extractor import (
    extract_javascript_import_dependencies,
)


def create_repo_file(root: Path, relative_path: str) -> None:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("// test module\n", encoding="utf-8")


def test_resolves_relative_named_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/users.js")

    source = """\
import { validateUser } from "./users.js";

export function processPayment() {
    validateUser();
}
"""

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/payment.js"
    assert dependencies[0].target_file == "src/users.js"
    assert dependencies[0].kind == "imports"


def test_resolves_default_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/logger.js")

    source = 'import logger from "./logger.js";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/logger.js"
    assert dependencies[0].kind == "imports"


def test_resolves_aliased_named_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/format.js")

    source = 'import { formatUser as format } from "./format.js";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/payment.js"
    assert dependencies[0].target_file == "src/format.js"
    assert dependencies[0].kind == "imports"


def test_ignores_external_package_import(tmp_path: Path) -> None:
    source = 'import express from "express";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert dependencies == []






def test_resolves_extensionless_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/users.js")

    source = 'import { validateUser } from "./users";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/users.js"


def test_ignores_missing_relative_import(tmp_path: Path) -> None:
    source = 'import { validateUser } from "./missing.js";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert dependencies == []


def test_ignores_import_that_escapes_repository(
    tmp_path: Path,
) -> None:
    outside_file = tmp_path.parent / "outside.js"
    outside_file.write_text("// outside\n", encoding="utf-8")

    source = 'import outside from "../outside.js";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert dependencies == []


def test_handles_malformed_javascript(tmp_path: Path) -> None:
    source = 'import { from "./users.js";\n'

    dependencies = extract_javascript_import_dependencies(
        tmp_path, "src/payment.js", source
    )

    assert dependencies == []
