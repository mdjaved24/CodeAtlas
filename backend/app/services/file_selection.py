
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath
from typing import Iterable


POLICY_VERSION = "1.0"

SUPPORTED_SOURCE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".java": "java",
    ".cs": "csharp",
}

EXCLUDED_DIRECTORIES = {
    ".git", ".hg", ".svn",
    "node_modules", "vendor",
    "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", "site-packages",
    "dist", "build", "target", "bin", "obj",
    ".next", ".nuxt", ".turbo", ".cache", "coverage",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
    ".pdf", ".zip", ".gz", ".tar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".class",
    ".jar", ".war", ".pyc", ".pyo",
    ".woff", ".woff2", ".ttf", ".otf",
    ".mp3", ".mp4", ".wav", ".avi",
    ".db", ".sqlite", ".sqlite3",
}

GENERATED_PATTERNS = {
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.generated.cs",
    "*.g.cs",
    "*.designer.cs",
    "*.pyc",
    "*.pyo",
}

SECRET_FILE_PATTERNS = {
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    "credentials.json",
    "secrets.json",
}

CONFIG_FILENAMES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini",
    "requirements.txt",
    "pipfile",
    "pipfile.lock",
    "poetry.lock",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "tsconfig.json",
    "jsconfig.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "gradle.properties",
    "global.json",
    "nuget.config",
    "directory.build.props",
    "directory.build.targets",
    ".editorconfig",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

CONFIG_PATTERNS = {
    "requirements*.txt",
    "*.csproj",
    "*.sln",
    "*.props",
    "*.targets",
    "tsconfig.*.json",
}

DOCUMENT_FILENAMES = {
    "readme.md",
    "contributing.md",
    "changelog.md",
    "architecture.md",
}

TEST_DIRECTORY_NAMES = {
    "test", "tests", "__tests__", "spec", "specs",
}


@dataclass(frozen=True)
class FileSelection:
    path: str
    selected: bool
    category: str
    reason: str
    language: str | None = None


def _matches_any(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatchcase(name, pattern) for pattern in patterns)


def _is_test_file(path: PurePosixPath) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    filename = path.name.lower()

    return (
        any(part in TEST_DIRECTORY_NAMES for part in lower_parts[:-1])
        or filename.startswith("test_")
        or ".test." in filename
        or ".spec." in filename
    )


def _mandatory_exclusion(
    path: PurePosixPath,
) -> tuple[str, str] | None:
    parts = [part.lower() for part in path.parts]
    filename = parts[-1]
    extension = PurePosixPath(filename).suffix.lower()

    if any(part in EXCLUDED_DIRECTORIES for part in parts[:-1]):
        return "excluded_directory", "Inside a dependency, metadata, or build directory"

    if _matches_any(filename, SECRET_FILE_PATTERNS):
        return "sensitive_file", "Matches a mandatory sensitive-file exclusion"

    if _matches_any(filename, GENERATED_PATTERNS):
        return "generated", "Generated or minified artifact"

    if extension in BINARY_EXTENSIONS:
        return "binary", "Known binary or archive file type"

    return None


def select_file(
    raw_path: str,
    include_patterns: Iterable[str] = (),
    exclude_patterns: Iterable[str] = (),
) -> FileSelection:
    """Make a deterministic selection decision for one relative path."""
    if (
        not raw_path
        or "\x00" in raw_path
        or "\\" in raw_path
        or raw_path.startswith("/")
        or ".." in raw_path.split("/")
        or ":" in raw_path.split("/")[0]
    ):
        return FileSelection(
            path=raw_path,
            selected=False,
            category="unsafe_path",
            reason="Path is not a safe repository-relative POSIX path",
        )

    path = PurePosixPath(raw_path)

    if not path.parts or str(path) in {"", "."}:
        return FileSelection(
            path=raw_path,
            selected=False,
            category="unsafe_path",
            reason="Path does not identify a repository file",
        )

    mandatory = _mandatory_exclusion(path)

    if mandatory is not None:
        category, reason = mandatory
        return FileSelection(
            path=raw_path,
            selected=False,
            category=category,
            reason=reason,
        )

    normalized = path.as_posix()

    if _matches_any(normalized, exclude_patterns):
        return FileSelection(
            path=raw_path,
            selected=False,
            category="user_excluded",
            reason="Matched a user exclusion pattern",
        )

    filename = path.name.lower()
    extension = path.suffix.lower()
    language = SUPPORTED_SOURCE_EXTENSIONS.get(extension)

    if language:
        if _is_test_file(path):
            return FileSelection(
                path=raw_path,
                selected=True,
                category="test",
                reason=f"Supported {language} test source",
                language=language,
            )

        return FileSelection(
            path=raw_path,
            selected=True,
            category="source",
            reason=f"Supported {language} source file",
            language=language,
        )

    if (
        filename in DOCUMENT_FILENAMES
        or (
            len(path.parts) > 1
            and path.parts[0].lower() in {"docs", "documentation"}
            and extension in {".md", ".rst", ".txt"}
        )
    ):
        return FileSelection(
            path=raw_path,
            selected=True,
            category="documentation",
            reason="Recognized repository documentation",
        )

    if (
        filename in CONFIG_FILENAMES
        or _matches_any(filename, CONFIG_PATTERNS)
    ):
        return FileSelection(
            path=raw_path,
            selected=True,
            category="configuration",
            reason="Recognized project configuration or dependency manifest",
        )

    if _matches_any(normalized, include_patterns):
        return FileSelection(
            path=raw_path,
            selected=True,
            category="user_included",
            reason="Matched a user include pattern",
        )

    return FileSelection(
        path=raw_path,
        selected=False,
        category="unsupported",
        reason="File type is not selected by the current policy",
    )


def select_files(
    paths: Iterable[str],
    include_patterns: Iterable[str] = (),
    exclude_patterns: Iterable[str] = (),
) -> list[FileSelection]:
    """Select a collection of repository-relative paths deterministically."""
    includes = tuple(include_patterns)
    excludes = tuple(exclude_patterns)

    return [
        select_file(path, includes, excludes)
        for path in sorted(paths)
    ]
