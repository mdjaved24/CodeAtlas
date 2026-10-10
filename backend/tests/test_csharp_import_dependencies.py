
from pathlib import Path

from app.services.dependencies.csharp_import_dependency_extractor import (
    extract_csharp_import_dependencies,
)


def create_repo_file(root: Path, relative_path: str) -> Path:
    file_path = root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("", encoding="utf-8")
    return file_path


def test_resolves_internal_namespace_import(tmp_path: Path) -> None:
    create_repo_file(
        tmp_path,
        "Services/UserService.cs",
    ).write_text(
        """\
namespace MyApp.Services
{
    public class UserService {}
}
""",
        encoding="utf-8",
    )

    source = """\
using MyApp.Services;

namespace MyApp.Controllers
{
    public class UserController {}
}
"""

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="Controllers/UserController.cs",
        source_code=source,
    )

    assert len(dependencies) == 1
    assert dependencies[0].source_file == "Controllers/UserController.cs"
    assert dependencies[0].target_file == "Services/UserService.cs"
    assert dependencies[0].kind == "imports"
    assert dependencies[0].line_number == 1


def test_ignores_framework_namespace_import(tmp_path: Path) -> None:
    source = """\
using System.Collections.Generic;

namespace MyApp
{
    public class UserService {}
}
"""

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="UserService.cs",
        source_code=source,
    )

    assert dependencies == []


def test_ignores_missing_internal_namespace_target(
    tmp_path: Path,
) -> None:
    source = """\
using MyApp.MissingServices;

namespace MyApp.Controllers
{
    public class UserController {}
}
"""

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="Controllers/UserController.cs",
        source_code=source,
    )

    assert dependencies == []




def test_supports_file_scoped_namespace(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "Services/UserService.cs").write_text(
        "namespace MyApp.Services;\npublic class UserService {}\n",
        encoding="utf-8",
    )

    source = """\
using MyApp.Services;

namespace MyApp.Controllers;

public class UserController {}
"""

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="Controllers/UserController.cs",
        source_code=source,
    )

    assert len(dependencies) == 1
    assert dependencies[0].target_file == "Services/UserService.cs"


def test_ignores_alias_using_directive(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "Services/UserService.cs").write_text(
        "namespace MyApp.Services { public class UserService {} }",
        encoding="utf-8",
    )

    source = """\
using ServiceAlias = MyApp.Services.UserService;

namespace MyApp.Controllers {}
"""

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="Controllers/UserController.cs",
        source_code=source,
    )

    assert dependencies == []


def test_rejects_source_path_traversal(tmp_path: Path) -> None:
    create_repo_file(tmp_path, "Services/UserService.cs").write_text(
        "namespace MyApp.Services { public class UserService {} }",
        encoding="utf-8",
    )

    source = "using MyApp.Services;\n"

    dependencies = extract_csharp_import_dependencies(
        repository_root=tmp_path,
        source_file="../outside/UserController.cs",
        source_code=source,
    )

    assert dependencies == []
