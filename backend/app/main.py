import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile

import tempfile
from pathlib import Path

from app.core.upload_limit import UploadRequestBodyLimitMiddleware
from tempfile import TemporaryDirectory
from app.services.zip_ingestion import (
    MAX_UPLOAD_BYTES,
    InvalidZipError,
    UploadTooLargeError,
    validate_zip_file,
    extract_zip_safely
)
from app.services.file_selection import select_files


app = FastAPI(
    title="CodeAtlas API",
    description="Codebase intelligence platform API",
    version="0.1.0"
)


app.add_middleware(UploadRequestBodyLimitMiddleware)


@app.get("/")
def root():
    return {
        "message": "Welcome to CodeAtlas API",
        "version": "0.1.0",
    }



@app.get("/health")
def health_check():
    return {
        "status":"ok",
        "service": "codeatlas-api",
    }



@app.post("/api/v1/repositories/upload-zip", status_code=201)
async def upload_repository_zip(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name

    if not filename.endswith('.zip'):
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have a .zip filename."
        )


    temp_path = None
    size_bytes = 0

    try:
        with tempfile.NamedTemporaryFile(
            prefix="codeatlas-upload-",
            suffix=".zip",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            while True:
                chunk = await file.read(1024*1024)

                if not chunk:
                    break

                size_bytes+=len(chunk)

                if size_bytes>MAX_UPLOAD_BYTES:
                    raise UploadTooLargeError("ZIP upload exceeds the 100 MiB limit.")

                temp_file.write(chunk)

        
        validated = validate_zip_file(temp_path, filename)

        with TemporaryDirectory(prefix="codeatlas-workspace-") as workspace:
            destination = Path(workspace) / "repository"

            extracted_count, expanded_bytes = extract_zip_safely(
                temp_path,
                destination,
            )

            # Only enumerate regular files inside the controlled workspace.
            repository_paths = [
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file() and not path.is_symlink()
            ]

            manifest = select_files(repository_paths)

            selected_count = sum(
                1 for item in manifest if item.selected
            )
            excluded_count = len(manifest) - selected_count

            return {
                "status": "accepted",
                "filename": validated.filename,
                "size_bytes": validated.size_bytes,
                "files_extracted": extracted_count,
                "expanded_bytes": expanded_bytes,
                "files_selected": selected_count,
                "files_excluded": excluded_count,
                "selection_policy_version": "1.0",
                "selection_manifest": [
                    {
                        "path": item.path,
                        "selected": item.selected,
                        "category": item.category,
                        "reason": item.reason,
                        "language": item.language,
                    }
                    for item in manifest
                ],
                "message": (
                    "ZIP validated, extracted, and file selection completed. "
                    "Temporary workspace will be cleaned up."
                ),
            }


    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except InvalidZipError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

        if temp_path is not None:
            temp_path.unlink(missing_ok=True)





if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
        )