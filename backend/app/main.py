import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

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
from app.services.source_parser import parse_selected_python_files


import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("codeatlas.ingestion")


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
async def upload_repository_zip(
    file: UploadFile = File(...),
    include_details: bool = Query(default=False),
):
    started_at = time.perf_counter()

    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".zip"):
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must have a .zip filename.",
        )

    temp_path = None
    size_bytes = 0

    # Initialize timings so the log remains safe if an early stage fails.
    upload_seconds = 0.0
    validation_seconds = 0.0
    extraction_seconds = 0.0
    enumeration_seconds = 0.0
    selection_seconds = 0.0
    parsing_seconds = 0.0
    response_build_seconds = 0.0

    try:
        # Stage 1: Upload to temporary storage.
        upload_started = time.perf_counter()

        with tempfile.NamedTemporaryFile(
            prefix="codeatlas-upload-",
            suffix=".zip",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size_bytes += len(chunk)

                if size_bytes > MAX_UPLOAD_BYTES:
                    raise UploadTooLargeError(
                        "ZIP upload exceeds the 100 MiB limit."
                    )

                temp_file.write(chunk)

        upload_seconds = time.perf_counter() - upload_started

        # Stage 2: Validate ZIP metadata.
        validation_started = time.perf_counter()

        validated = validate_zip_file(temp_path, filename)

        validation_seconds = time.perf_counter() - validation_started

        with TemporaryDirectory(
            prefix="codeatlas-workspace-"
        ) as workspace:
            destination = Path(workspace) / "repository"

            # Stage 3: Safely extract the archive.
            extraction_started = time.perf_counter()

            extracted_count, expanded_bytes = extract_zip_safely(
                temp_path,
                destination,
            )

            extraction_seconds = (
                time.perf_counter() - extraction_started
            )

            # Stage 4: Enumerate extracted files.
            enumeration_started = time.perf_counter()

            repository_paths = [
                path.relative_to(destination).as_posix()
                for path in destination.rglob("*")
                if path.is_file() and not path.is_symlink()
            ]

            enumeration_seconds = (
                time.perf_counter() - enumeration_started
            )

            # Stage 5: Apply file-selection policy.
            selection_started = time.perf_counter()

            manifest = select_files(repository_paths)

            selected_count = sum(
                1 for item in manifest if item.selected
            )
            excluded_count = len(manifest) - selected_count

            selection_seconds = (
                time.perf_counter() - selection_started
            )

            # Stage 6: Parse selected Python files.
            parsing_started = time.perf_counter()

            parse_results = parse_selected_python_files(
                repository_root=destination,
                manifest=manifest,
            )

            files_parsed = len(parse_results)

            symbols_extracted = sum(
                len(result.symbols)
                for result in parse_results
            )

            parse_failures = sum(
                1
                for result in parse_results
                if result.status == "failed"
            )

            parsing_seconds = (
                time.perf_counter() - parsing_started
            )

            # Stage 7: Build the API response.
            response_build_started = time.perf_counter()

            
            response = {
                "status": "accepted",
                "filename": validated.filename,
                "size_bytes": validated.size_bytes,
                "files_extracted": extracted_count,
                "expanded_bytes": expanded_bytes,
                "files_selected": selected_count,
                "files_excluded": excluded_count,
                "selection_policy_version": "1.0",
                "files_parsed": files_parsed,
                "symbols_extracted": symbols_extracted,
                "parse_failures": parse_failures,
                "details_included": include_details,
                "message": (
                    "ZIP validated, extracted, and file selection completed. "
                    "Temporary workspace will be cleaned up."
                ),
            }

            if include_details:
                response["selection_manifest"] = [
                    {
                        "path": item.path,
                        "selected": item.selected,
                        "category": item.category,
                        "reason": item.reason,
                        "language": item.language,
                    }
                    for item in manifest
                ]

                response["parse_results"] = [
                    result.model_dump()
                    for result in parse_results
                ]


            response_build_seconds = (
                time.perf_counter() - response_build_started
            )

            total_seconds = time.perf_counter() - started_at

            print("DEBUG: ingestion timing statement reached", flush=True)

            logger.info(
                (
                    "Repository ingestion timings | "
                    "upload=%.2fs validation=%.2fs "
                    "extraction=%.2fs enumeration=%.2fs "
                    "selection=%.2fs parsing=%.2fs "
                    "response_build=%.2fs total=%.2fs | "
                    "compressed_bytes=%d expanded_bytes=%d "
                    "files=%d selected=%d parsed=%d symbols=%d"
                ),
                upload_seconds,
                validation_seconds,
                extraction_seconds,
                enumeration_seconds,
                selection_seconds,
                parsing_seconds,
                response_build_seconds,
                total_seconds,
                validated.size_bytes,
                expanded_bytes,
                extracted_count,
                selected_count,
                files_parsed,
                symbols_extracted,
            )

            logger.info("DEBUG: about to return upload response")

            return response

    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=str(exc),
        ) from exc

    except InvalidZipError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

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