
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.services.zip_ingestion import (
    InvalidZipError,
    UploadTooLargeError,
    inspect_zip_metadata,
    validate_zip_file,
    extract_zip_safely
)


def create_test_zip(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("README.md", "# Sample repository")


def test_validate_zip_file_accepts_valid_archive(tmp_path):
    zip_path = tmp_path / "repository.zip"
    create_test_zip(zip_path)

    result = validate_zip_file(zip_path, "repository.zip")

    assert result.filename == "repository.zip"
    assert result.size_bytes == zip_path.stat().st_size


def test_validate_zip_file_rejects_non_zip_file(tmp_path):
    file_path = tmp_path / "not-a-zip.zip"
    file_path.write_text("This is not a ZIP archive.", encoding="utf-8")

    with pytest.raises(InvalidZipError):
        validate_zip_file(file_path, "not-a-zip.zip")


def test_validate_zip_file_rejects_oversized_file(tmp_path, monkeypatch):
    file_path = tmp_path / "large.zip"
    create_test_zip(file_path)

    # Use a small limit so the test doesn't need a 100 MiB file.
    import app.services.zip_ingestion as ingestion

    monkeypatch.setattr(ingestion, "MAX_UPLOAD_BYTES", 10)

    with pytest.raises(UploadTooLargeError):
        validate_zip_file(file_path, "large.zip")




def test_inspect_zip_metadata_rejects_parent_traversal(tmp_path):
    zip_path = tmp_path / "unsafe.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    with ZipFile(zip_path) as archive:
        with pytest.raises(InvalidZipError):
            inspect_zip_metadata(archive)


def test_inspect_zip_metadata_rejects_oversized_entry(
    tmp_path, monkeypatch
):
    import app.services.zip_ingestion as ingestion

    zip_path = tmp_path / "large-entry.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("large.txt", "A" * 100)

    monkeypatch.setattr(ingestion, "MAX_SINGLE_FILE_BYTES", 50)

    with ZipFile(zip_path) as archive:
        with pytest.raises(InvalidZipError):
            inspect_zip_metadata(archive)





def test_extract_zip_safely_extracts_valid_archive(tmp_path):
    zip_path = tmp_path / "repository.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("README.md", "# CodeAtlas")
        archive.writestr("src/example.py", "print('hello')")

    destination = tmp_path / "extracted"

    file_count, total_bytes = extract_zip_safely(
        zip_path,
        destination,
    )

    assert file_count == 2
    assert total_bytes == len("# CodeAtlas") + len("print('hello')")
    assert (destination / "README.md").read_text() == "# CodeAtlas"
    assert (destination / "src" / "example.py").exists()


def test_extract_zip_safely_rejects_traversal(tmp_path):
    zip_path = tmp_path / "unsafe.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    destination = tmp_path / "extracted"
    outside_file = tmp_path / "outside.txt"

    with pytest.raises(InvalidZipError):
        extract_zip_safely(zip_path, destination)

    assert not outside_file.exists()
    assert not destination.exists()


def test_extract_zip_safely_removes_partial_output_on_failure(
    tmp_path, monkeypatch
):
    import app.services.zip_ingestion as ingestion

    zip_path = tmp_path / "too-large.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("first.txt", "small")
        archive.writestr("second.txt", "A" * 100)

    monkeypatch.setattr(ingestion, "MAX_SINGLE_FILE_BYTES", 50)

    destination = tmp_path / "extracted"

    with pytest.raises(InvalidZipError):
        extract_zip_safely(zip_path, destination)

    assert not destination.exists()




def test_inspect_zip_metadata_rejects_duplicate_paths(tmp_path):
    zip_path = tmp_path / "duplicate.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("README.md", "first")
        archive.writestr("README.md", "second")

    with ZipFile(zip_path) as archive:
        with pytest.raises(InvalidZipError, match="duplicate paths"):
            inspect_zip_metadata(archive)


def test_inspect_zip_metadata_rejects_file_directory_conflict(
    tmp_path,
):
    zip_path = tmp_path / "conflict.zip"

    with ZipFile(zip_path, "w") as archive:
        archive.writestr("src", "this is a file")
        archive.writestr("src/main.py", "print('hello')")

    with ZipFile(zip_path) as archive:
        with pytest.raises(
            InvalidZipError,
            match="conflicting file and directory paths",
        ):
            inspect_zip_metadata(archive)
