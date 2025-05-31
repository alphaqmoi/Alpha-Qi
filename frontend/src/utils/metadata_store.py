# utils/metadata_store.py
def rename_file_metadata(old_uri: str, new_uri: str):
    # For JSON-based storage
    with open("metadata.json", "r+") as f:
        metadata = json.load(f)
        metadata[new_uri] = metadata.pop(old_uri, {})
        f.seek(0)
        json.dump(metadata, f, indent=2)
        f.truncate()
