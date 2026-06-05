class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidFileTypeException(AppException):
    def __init__(self, mime_type: str):
        super().__init__(
            f"Unsupported file type: '{mime_type}'. Supported types: text/csv",
            status_code=415
        )


class FileTooLargeException(AppException):
    def __init__(self):
        super().__init__("File exceeds maximum allowed size of 1GB.", status_code=413)


class EmptyFileException(AppException):
    def __init__(self):
        super().__init__("Uploaded file is empty.", status_code=400)


class UploadJobNotFoundException(AppException):
    def __init__(self, job_id: str):
        super().__init__(f"Upload job '{job_id}' not found.", status_code=404)