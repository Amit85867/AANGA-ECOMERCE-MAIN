"""Admin file upload. Kept for the forms that post here; the image is stored
and catalogued exactly as an upload to the media library is."""
from flask import request, jsonify

from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required


@admin_bp.route("/upload", methods=["POST"])
@admin_required
def upload_image():
    from app.routes.admin.merchandising import store_upload

    if "file" not in request.files:
        return jsonify(error="No file provided"), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify(error="Empty file"), 400
    asset, failure = store_upload(f)
    if failure:
        return jsonify(error=failure[0]), failure[1]
    return jsonify(url=asset.url, id=asset.id), 201
