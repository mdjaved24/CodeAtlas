
from starlette.responses import JSONResponse

from app.services.zip_ingestion import MAX_UPLOAD_BYTES


# Allow limited multipart form overhead beyond the ZIP itself.
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024


class RequestBodyTooLarge(Exception):
    pass


class UploadRequestBodyLimitMiddleware:
    """Bound the total request body for the ZIP upload endpoint."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("path") != "/api/v1/repositories/upload-zip"
            or scope.get("method") != "POST"
        ):
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get(b"content-length")

        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                response = JSONResponse(
                    {"detail": "Invalid Content-Length header."},
                    status_code=400,
                )
                await response(scope, receive, send)
                return

            if declared_length < 0:
                response = JSONResponse(
                    {"detail": "Invalid Content-Length header."},
                    status_code=400,
                )
                await response(scope, receive, send)
                return

            if declared_length > MAX_REQUEST_BYTES:
                response = JSONResponse(
                    {"detail": "Upload request exceeds the allowed size."},
                    status_code=413,
                )
                await response(scope, receive, send)
                return

        received_bytes = 0

        async def limited_receive():
            nonlocal received_bytes
            message = await receive()

            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))

                if received_bytes > MAX_REQUEST_BYTES:
                    raise RequestBodyTooLarge()

            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                {"detail": "Upload request exceeds the allowed size."},
                status_code=413,
            )
            await response(scope, receive, send)
