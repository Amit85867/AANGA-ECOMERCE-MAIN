"""Admin file upload: product images."""
import os

from flask import request, jsonify, current_app

from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services.storage import save_image, StorageError

ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_SIZE = 5 * 1024 * 1024


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@admin_bp.route("/upload", methods=["POST"])
@admin_required
def upload_image():
    if "file" not in request.files:
        return jsonify(error="No file provided"), 400

    f = request.files["file"]
    if not f or not f.filename:
        return jsonify(error="Empty file"), 400

    if not _allowed(f.filename):
        return jsonify(error=f"Allowed types: {', '.join(ALLOWED)}"), 400

    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_SIZE:
        return jsonify(error="File too large (max 5 MB)"), 400

    try:
        url = save_image(f)
    except StorageError as exc:
        current_app.logger.error("Image upload failed: %s", exc)
        return jsonify(error="Could not store the image. Please try again."), 502

    return jsonify(url=url), 201
