from flask import Blueprint, request, jsonify
import os
import subprocess
import shutil

rename_file_bp = Blueprint("rename_file", __name__)

METADATA_DIR = "savedFiles/.metadata"

def uri_to_path(uri: str) -> str:
    if uri.startswith("file://"):
        return uri[7:]
    return uri

def git_rename(old_path: str, new_path: str):
    subprocess.run(["git", "mv", old_path, new_path], check=True)
    subprocess.run(["git", "add", new_path], check=True)

def rename_metadata(old_uri: str, new_uri: str):
    old_base = os.path.splitext(os.path.basename(uri_to_path(old_uri)))[0]
    new_base = os.path.splitext(os.path.basename(uri_to_path(new_uri)))[0]
    old_meta_path = os.path.join(METADATA_DIR, f"{old_base}.metadata.json")
    new_meta_path = os.path.join(METADATA_DIR, f"{new_base}.metadata.json")
    if os.path.exists(old_meta_path):
        os.makedirs(METADATA_DIR, exist_ok=True)
        shutil.move(old_meta_path, new_meta_path)

@rename_file_bp.route("/api/renameFile", methods=["POST"])
def rename_file():
    data = request.json
    old_uri = data.get("oldUri")
    new_uri = data.get("newUri")
    if not old_uri or not new_uri:
        return jsonify({"success": False, "message": "Missing oldUri or newUri"}), 400

    try:
        old_path = uri_to_path(old_uri)
        new_path = uri_to_path(new_uri)

        os.rename(old_path, new_path)
        git_rename(old_path, new_path)
        rename_metadata(old_uri, new_uri)

        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in rename_file: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
