
from pathlib import Path

from app.services.dependencies.typescript_import_dependency_extractor import extract_typescript_import_dependencies


def create_repo_file(root: Path, relative_path: str) -> None:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("// test module\n", encoding="utf-8")


def test_resolves_named_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/users.ts")

    source = """\
import { validateUser } from "./users";

export function processPayment(): void {
    validateUser();
}
"""

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/payment.ts", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "src/payment.ts"
    assert dependencies[0].target_file == "src/users.ts"
    assert dependencies[0].kind == "imports"


def test_resolves_default_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/logger.ts")

    source = 'import logger from "./logger";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/payment.ts", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/logger.ts"


def test_resolves_aliased_named_import(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/format.ts")

    source = 'import { formatUser as format } from "./format";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/payment.ts", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/format.ts"


def test_ignores_external_package_import(tmp_path: Path) -> None:
    source = 'import axios from "axios";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/payment.ts", source
    )

    assert dependencies == []




def test_resolves_tsx_target(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/components/Button.tsx")

    source = 'import Button from "./components/Button";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/App.tsx", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/components/Button.tsx"


def test_resolves_directory_index_tsx(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "src/components/index.tsx")

    source = 'import Components from "./components";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/App.ts", source
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "src/components/index.tsx"


def test_ignores_missing_import_target(tmp_path: Path) -> None:
    source = 'import { missing } from "./missing";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/App.ts", source
    )

    assert dependencies == []


def test_ignores_import_outside_repository(tmp_path: Path) -> None:
    outside_file = tmp_path.parent / "outside.ts"
    outside_file.write_text("// outside\n", encoding="utf-8")

    source = 'import outside from "../outside";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/App.ts", source
    )

    assert dependencies == []


def test_handles_malformed_typescript(tmp_path: Path) -> None:
    source = 'import { from "./users";\n'

    dependencies = extract_typescript_import_dependencies(
        tmp_path, "src/App.ts", source
    )

    assert dependencies == []
