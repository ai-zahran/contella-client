from email_validator import validate_email, EmailNotValidError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class PDFUploadValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size_mb: int = 10, target_paths: list[str] = None):
        super().__init__(app)
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.target_paths = target_paths if target_paths else ["/upload-pdf/"]

    async def dispatch(self, request: Request, call_next):
        # Check if the request path is in the target paths
        if any(request.url.path.startswith(path) for path in self.target_paths):

            # Only process multipart requests
            if request.headers.get("content-type", "").startswith("multipart/form-data"):

                body = await request.body()  # Read the body once
                request._body = body  # Store the body for later

                form = await request.form()

                if set(form.keys()) != {"email", "pdfFile"}:
                    return JSONResponse({"error": "Form is invalid"}, status_code=400)

                is_email_valid, _ = validate_and_normalize_email(form["email"])
                if not is_email_valid:
                    return JSONResponse({"error": "Email is invalid"}, status_code=400)

                pdf_file = form["pdfFile"]
                if (
                        not hasattr(pdf_file, "content_type")
                        or hasattr(pdf_file, "content_type") and pdf_file.content_type != "application/pdf"
                ):
                    return JSONResponse({"error": "Only PDF files are allowed."}, status_code=400)

                if not hasattr(pdf_file, "size") or hasattr(pdf_file, "size") and pdf_file.size > self.max_size_bytes:
                    return JSONResponse({"error": "File size exceeds the 10 MB limit."}, status_code=400)

                # If everything is valid, store form data in state or attributes
                request.state.form_data = form  # Pass to the endpoint if needed
        response = await call_next(request)
        return response


def validate_and_normalize_email(email: str):
    try:
        email_info = validate_email(email, check_deliverability=False)
        return True, email_info.normalized
    except EmailNotValidError:
        return False, None
