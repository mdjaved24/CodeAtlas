
from io import BytesIO
from zipfile import ZipFile

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
        "/api/v1/repositories/upload-zip",
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
