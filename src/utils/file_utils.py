import hashlib
import os


def get_files_in_directory(directory):
    """
    Get all Markdown and JSON files in a specified directory.
    Args:
        directory (str): Path to the directory to search for files.
    Returns:
        list: List of file paths for Markdown and JSON files.
    """
    files = []
    for filename in os.listdir(directory):
        if filename.endswith(".md") or filename.endswith(".json"):
            files.append(os.path.join(directory, filename))
    return files


def get_hash_from_files(file_paths):
    """
    Generate SHA256 hashes for a list of file paths.
    Args:
        file_paths (list): List of file paths to hash.
    Returns:
        list: List of SHA256 hashes for the files.
    """
    sha256_hash = hashlib.sha256()
    hashes = []

    for file_path in file_paths:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        hashes.append(sha256_hash.hexdigest())

    return hashes