import os

from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def validate_document(upload):
    """Only PDF or image files up to 2 MB are accepted."""
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Upload a PDF, JPG or PNG file.")
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError("The file is larger than 2 MB.")
