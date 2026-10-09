from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import stat
from pathlib import PurePosixPath
import shutil


MAX_UPLOAD_BYTES = 100*1024*1024   # 100 MB

MAX_EXPANDED_BYTES = 500 * 1024 * 1024  # 500 MiB
MAX_FILE_COUNT = 20_000
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024  # 10 MiB
MAX_COMPRESSION_RATIO = 100




class ZipIngestionError(Exception):
    """Raised when a repository ZIP fails validation."""


class UploadTooLargeError(ZipIngestionError):
    """Raised when an upload exceeds the configured size limit."""


class InvalidZipError(ZipIngestionError):
    """Raised when the uploaded file is not a valid ZIP archive."""


@dataclass(frozen=True)
class ValidatedZip:
    filename: str
    size_bytes: int



def inspect_zip_metadata(archive: ZipFile) -> tuple[int, int]:
    """
    Check archive metadata before decompressing any members.

    Returns:
        (regular_file_count, declared_expanded_bytes)
    """
    file_count = 0
    expanded_bytes = 0
    seen_paths: dict[str, bool] = {}

    entries = archive.infolist()

    if len(entries)>MAX_FILE_COUNT:
        raise InvalidZipError("ZIP contains too many entries.")

    for info in entries:
        name = info.filename

        # ZIP paths conventionally use forward slashes.
        # Reject Windows separators and absolute or traversal paths.
        if not name or "\x00" in name or "\\" in name:
            raise InvalidZipError("ZIP contains an unsafe path.")

        path = PurePosixPath(name)

        if path.is_absolute() or ".." in path.parts:
            raise InvalidZipError("ZIP contains an unsafe path.")

        # Reject Windows drive-style paths, including C:/file.txt.
        if path.parts and ":" in path.parts[0]:
            raise InvalidZipError("ZIP contains an unsafe path.")

        
        normalized = str(path)
        is_directory = info.is_dir()

        if normalized in seen_paths:
            raise InvalidZipError("ZIP contains duplicate paths.")

        # A file cannot also serve as a parent directory.
        for parent in path.parents:
            parent_name = str(parent)

            if parent_name == ".":
                continue

            if (
                parent_name in seen_paths
                and not seen_paths[parent_name]
            ):
                raise InvalidZipError(
                    "ZIP contains conflicting file and directory paths."
                )

        # A path cannot be a file if other entries already exist beneath it.
        if not is_directory and any(
            existing.startswith(normalized + "/")
            for existing in seen_paths
        ):
            raise InvalidZipError(
                "ZIP contains conflicting file and directory paths."
            )

        seen_paths[normalized] = is_directory

        # Detect symbolic links and special Unix filesystem entries.
        unix_mode = info.external_attr >> 16
        file_type = stat.S_IFMT(unix_mode)

        if file_type not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise InvalidZipError("ZIP contains an unsupported file type.")

        if info.flag_bits & 0x1:
            raise InvalidZipError("Encrypted ZIP entries are not supported.")

        if info.is_dir():
            continue

        file_count+=1

        if info.file_size>MAX_SINGLE_FILE_BYTES:
            raise InvalidZipError("ZIP contains a file exceeding 10 MiB.")

        expanded_bytes+=info.file_size

        if expanded_bytes>MAX_EXPANDED_BYTES:
            raise InvalidZipError("ZIP exceeds the expanded-size limit.")

        if info.file_size>0 and info.compress_size==0:
            raise InvalidZipError("ZIP contains a suspicious compressed entry.")

        if info.compress_size>0:
            ratio = info.file_size/info.compress_size

            if ratio > MAX_COMPRESSION_RATIO:
                raise InvalidZipError(
                    "ZIP contains an entry with an excessive compression ratio."
                )

    return file_count, expanded_bytes




def validate_zip_file(path: Path, filename: str) -> ValidatedZip:
    """
    Validate the uploaded file's size and basic ZIP structure.

    This function does not extract files.
    """
    size_bytes = path.stat().st_size

    if size_bytes>MAX_UPLOAD_BYTES:
        raise UploadTooLargeError("ZIP upload exceeds the 100 MiB limit.")

    try:
        with ZipFile(path) as archive:
            file_count, expanded_bytes = inspect_zip_metadata(archive)

    except InvalidZipError:
        raise

    except (BadZipFile, OSError, EOFError) as exc:
        raise InvalidZipError("Uploaded file is not a valid ZIP archive.") from exc

    return ValidatedZip(filename=filename, size_bytes=size_bytes)




def extract_zip_safely(archive_path: Path, destination:Path)->tuple[int, int]:
    """
    Safely extract a validated ZIP into a new directory.

    Returns:
        (number_of_files, actual_bytes_written)

    The destination must not already exist. On failure, partial
    extracted contents are removed.
    """
    if destination.exists():
         raise ZipIngestionError("Extraction destination already exists.")

    destination.mkdir(parents=True, exist_ok=False)
    root = destination.resolve()

    file_count = 0
    total_bytes = 0

    try:
        with ZipFile(archive_path) as archive:
            # Reject suspicious entries before decompressing any of them.
            inspect_zip_metadata(archive)

            for info in archive.infolist():
                name = info.filename

                # Recheck path components before creating anything.
                if (
                    not name
                    or "\x00" in name
                    or "\\" in name
                ):
                    raise InvalidZipError("ZIP contains an unsafe path.")

                relative_path = PurePosixPath(name)

                if (
                    relative_path.is_absolute()
                    or ".." in relative_path.parts
                    or (
                        relative_path.parts
                        and ":" in relative_path.parts[0]
                    )
                ):
                    raise InvalidZipError("ZIP contains an unsafe path.")


                # Directory entries may end with a slash.
                if info.is_dir():
                    relative_path = PurePosixPath(
                        name.rstrip("/")
                    )

                target = root.joinpath(*relative_path.parts).resolve()

                try:
                    target.relative_to(root)
                except ValueError as exc:
                    raise InvalidZipError(
                        "ZIP entry escapes the extraction directory."
                    ) from exc

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                file_count += 1

                if file_count>MAX_FILE_COUNT:
                    raise InvalidZipError("ZIP contains too many files.")

                target.parent.mkdir(parents=True, exist_ok=True)

                actual_file_bytes = 0

                # Read in bounded chunks and enforce limits on actual
                # decompressed bytes, not just ZIP metadata.

                with archive.open(info, "r") as source:
                    with target.open("xb") as output:
                        while True:
                            chunk = source.read(64 * 1024)

                            if not chunk:
                                break

                            actual_file_bytes += len(chunk)
                            total_bytes += len(chunk)

                            if actual_file_bytes > MAX_SINGLE_FILE_BYTES:
                                raise InvalidZipError(
                                    "Extracted file exceeds the 10 MiB limit."
                                )

                            if total_bytes > MAX_EXPANDED_BYTES:
                                raise InvalidZipError(
                                    "Extracted data exceeds the 500 MiB limit."
                                )

                            output.write(chunk)

                if actual_file_bytes != info.file_size:
                    raise InvalidZipError(
                        "ZIP entry size does not match its metadata."
                    )

        return file_count, total_bytes

    except BadZipFile as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise InvalidZipError(
            "ZIP archive is corrupted or failed integrity validation."
        ) from exc

    except BaseException:
        # Never leave partially extracted data behind.
        shutil.rmtree(destination, ignore_errors=True)
        raise


                




     