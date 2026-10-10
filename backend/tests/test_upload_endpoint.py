
from io import BytesIO
import io
from zipfile import ZipFile
import zipfile

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def make_zip_bytes() -> bytes:
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# Example repository")

    return buffer.getvalue()



def test_upload_endpoint_accepts_valid_zip():
    response = client.post(
        "/api/v1/repositories/upload-zip",
        files={
            "file": (
                "example.zip",
                make_zip_bytes(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "accepted"
    assert response.json()["filename"] == "example.zip"


def test_upload_endpoint_rejects_non_zip_filename():
    response = client.post(
        "/api/v1/repositories/upload-zip",
        files={
            "file": (
                "notes.txt",
                b"not a zip",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_upload_endpoint_rejects_corrupted_zip():
    response = client.post(
        "/api/v1/repositories/upload-zip",
        files={
            "file": (
                "broken.zip",
                b"not a valid ZIP archive",
                "application/zip",
            )
        },
    )

    assert response.status_code == 400




def test_upload_endpoint_reports_extraction_results():
    response = client.post(
        "/api/v1/repositories/upload-zip",
        files={
            "file": (
                "example.zip",
                make_zip_bytes(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["status"] == "accepted"
    assert body["files_extracted"] == 1
    assert body["expanded_bytes"] > 0
    assert "Temporary workspace will be cleaned up" in body["message"]




def test_upload_endpoint_rejects_path_traversal():
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        archive.writestr("../outside.txt", "unsafe content")

    response = client.post(
        "/api/v1/repositories/upload-zip",
        files={
            "file": (
                "unsafe.zip",
                buffer.getvalue(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 400
    assert "unsafe path" in response.json()["detail"].lower()




def test_upload_endpoint_returns_file_selection_manifest():
    buffer = BytesIO()

    with ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# Example")
        archive.writestr("src/main.py", "print('hello')")
        archive.writestr("node_modules/example/index.js", "ignored")
        archive.writestr("assets/logo.png", b"not-analyzed-image")

    response = client.post(
        "/api/v1/repositories/upload-zip?include_details=true",
        files={
            "file": (
                "example.zip",
                buffer.getvalue(),
                "application/zip",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["files_extracted"] == 4
    assert body["files_selected"] == 2
    assert body["files_excluded"] == 2
    assert body["selection_policy_version"] == "1.0"

    manifest = {
        item["path"]: item
        for item in body["selection_manifest"]
    }

    assert manifest["src/main.py"]["selected"] is True
    assert manifest["src/main.py"]["language"] == "python"

    assert manifest["node_modules/example/index.js"]["selected"] is False
    assert manifest["node_modules/example/index.js"]["category"] == (
        "excluded_directory"
    )

    assert manifest["assets/logo.png"]["selected"] is False
    assert manifest["assets/logo.png"]["category"] == "binary"


def test_upload_parses_selected_supported_source_files():
    client = TestClient(app)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as archive:
        archive.writestr(
            "src/payments.py",
            "class PaymentService:\n"
            "    def process_payment(self):\n"
            "        pass\n",
        )
        archive.writestr(
            "src/app.js",
            "function startApp() {}",
        )
        archive.writestr(
            "README.md",
            "# CodeAtlas",
        )

    zip_buffer.seek(0)

    response = client.post(
        "/api/v1/repositories/upload-zip?include_details=true",
        files={
            "file": (
                "repository.zip",
                zip_buffer,
                "application/zip",
            )
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["files_parsed"] == 2
    assert body["parse_failures"] == 0
    assert body["symbols_extracted"] == 3

    results = body["parse_results"]

    assert len(results) == 2

    parsed_paths = {
        result["file_path"]
        for result in results
    }

    assert parsed_paths == {
        "src/payments.py",
        "src/app.js",
    }

    assert "README.md" not in parsed_paths
    python_result = next(
    result
    for result in results
    if result["file_path"] == "src/payments.py"
    )

    javascript_result = next(
        result
        for result in results
        if result["file_path"] == "src/app.js"
    )

    assert python_result["language"] == "python"
    assert javascript_result["language"] == "javascript"
    assert python_result["status"] == "success"
    assert [
        symbol["name"] for symbol in python_result["symbols"]
    ] == ["PaymentService", "process_payment"]

    assert javascript_result["status"] == "success"
    assert [
        symbol["name"] for symbol in javascript_result["symbols"]
    ] == ["startApp"]