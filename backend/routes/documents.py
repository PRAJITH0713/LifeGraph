"""Private document upload endpoint."""

from flask import Blueprint, current_app, jsonify, request

from services.document_service import DocumentValidationError, store_document

documents_api = Blueprint("documents_api", __name__, url_prefix="/api/documents")


@documents_api.post("/upload")
def upload_document():
    uploaded_file = request.files.get("document")
    if uploaded_file is None:
        return jsonify({"error": "Select a document to upload."}), 400

    try:
        result = store_document(
            uploaded_file,
            current_app.config["UPLOAD_DIRECTORY"],
            current_app.config["MAX_UPLOAD_SIZE_BYTES"],
        )
    except DocumentValidationError as error:
        return jsonify({"error": str(error)}), 400
    except OSError:
        current_app.logger.exception("Could not store uploaded document.")
        return jsonify({"error": "The document could not be stored. Please try again."}), 500

    return jsonify(
        {
            "filename": result["filename"],
            "size": result["size"],
            "message": "Document stored privately. No text extraction or analysis was performed.",
        }
    ), 201
