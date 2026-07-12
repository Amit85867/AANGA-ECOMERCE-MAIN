"""Admin file upload: product images."""
import os
import uuid

from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required

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

    ext = f.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = os.path.join(current_app.root_path, "..", "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    f.save(os.path.join(upload_dir, filename))

    url = f"/static/uploads/{filename}"
    return jsonify(url=url), 201
