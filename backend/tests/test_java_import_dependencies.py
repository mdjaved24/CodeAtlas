
from pathlib import Path

from app.services.dependencies.java_import_dependency_extractor import (
    extract_java_import_dependencies,
)


def create_repo_file(root: Path, relative_path: str) -> None:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("// test source\n", encoding="utf-8")


def test_resolves_fully_qualified_import(tmp_path: Path) -> None:
    create_repo_file(
        tmp_path,
        "src/main/java/com/example/users/UserService.java",
    )

    source = """\
package com.example;

import com.example.users.UserService;

public class PaymentService {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == (
        "src/main/java/com/example/PaymentService.java"
    )
    assert dependencies[0].target_file == (
        "src/main/java/com/example/users/UserService.java"
    )
    assert dependencies[0].kind == "imports"


def test_ignores_jdk_import(tmp_path: Path) -> None:
    source = """\
package com.example;

import java.util.List;

public class PaymentService {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert dependencies == []


def test_ignores_missing_internal_import(tmp_path: Path) -> None:
    source = """\
package com.example;

import com.example.users.MissingService;

public class PaymentService {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert dependencies == []


def test_ignores_static_external_import(tmp_path: Path) -> None:
    source = """\
package com.example;

import static org.junit.Assert.assertEquals;

public class PaymentService {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert dependencies == []




def test_resolves_import_from_src_test_java(tmp_path: Path) -> None:
    create_repo_file(
        tmp_path,
        "src/test/java/com/example/TestHelper.java",
    )

    source = """\
package com.example;

import com.example.TestHelper;

public class PaymentServiceTest {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/test/java/com/example/PaymentServiceTest.java",
        source,
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == (
        "src/test/java/com/example/TestHelper.java"
    )


def test_ignores_missing_java_source_file(tmp_path: Path) -> None:
    source = """\
package com.example;

import com.example.users.MissingService;

public class PaymentService {}
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert dependencies == []


def test_handles_malformed_java(tmp_path: Path) -> None:
    source = """\
package com.example;

import com.example.users.UserService

public class PaymentService {
"""

    dependencies = extract_java_import_dependencies(
        tmp_path,
        "src/main/java/com/example/PaymentService.java",
        source,
    )

    assert dependencies == []
