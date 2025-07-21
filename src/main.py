from datetime import datetime, timezone
import hashlib
import os
from dotenv import load_dotenv
from openai import OpenAI
from supabase import Client, create_client
from services.api_service import fetch_articles, save_article_as_md
from services.vector_store_service import VectorStoreService

load_dotenv()

OUTPUT_DIR = "articles_md"


def get_hash_from_files(file_paths):
    sha256_hash = hashlib.sha256()
    hashes = []

    for file_path in file_paths:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        hashes.append(sha256_hash.hexdigest())

    return hashes


def get_files_in_directory(directory):
    files = []
    for filename in os.listdir(directory):
        if filename.endswith(".md") or filename.endswith(".json"):
            files.append(os.path.join(directory, filename))
    return files


def main():
    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Total articles fetched: {len(articles)}")

    for article in articles:
        save_article_as_md(article)

    print(f"Saved all Markdown files in '{OUTPUT_DIR}' folder.")

    added = 0
    updated = 0
    skipped = 0
    deleted = 0

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    response = (
        supabase.table("scraped_articles")
        .select("hash", "updated_at", "id", "file_id")
        .execute()
    )
    # return
    old_data = {item["id"]: item for item in response.data}
    old_hashes = set(item["hash"] for item in response.data)
    old_ids = set(str(item["id"]) for item in response.data)

    new_files = get_files_in_directory(OUTPUT_DIR)
    new_hashes = get_hash_from_files(new_files)

    new_ids = set(file.split(os.sep)[-1].split("_")[0] for file in new_files)

    deleted_ids = old_ids - new_ids
    print(f"New files: {len(new_files)}, Old files: {len(old_ids)}, Deleted files: {len(deleted_ids)}")

    old_docs = {
        str(item["id"]): {
            "id": item["id"],
            "hash": item["hash"],
            "updated_at": item["updated_at"],
            "file_id": item["file_id"],
        }
        for item in response.data
    }

    new_docs = [
        {
            "id": file.split(os.sep)[-1].split("_")[0],
            # "file_id": file.split(os.sep)[-1],
            "hash": hash_value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "file_path": file,
        }
        for file, hash_value in zip(new_files, new_hashes)
    ]

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    vector_store_id = os.environ.get("VECTOR_STORE_ID")

    vector_store_service = VectorStoreService(
        client=client, vector_store_id=vector_store_id
    )
    for doc_id in deleted_ids:
        result = supabase.table("scraped_articles").delete(returning="representation").eq("id", doc_id).execute()
        vector_store_service.delete_file(result.data[0]["file_id"])
        deleted += 1

    docs_update = []
    docs_add = []
    
    for docs in new_docs:
        if docs["hash"] in old_hashes:
            # Old scrape
            skipped += 1
        elif docs["id"] in old_docs:
            # Update scrape
            docs_update.append(docs)
            cleaned_doc = {
                "id": docs["id"],
                "hash": docs["hash"],
                "updated_at": docs["updated_at"],
            }
            try:
                file_stream = open(docs["file_path"], "rb")
                file_id = vector_store_service.update_file(old_docs[docs["id"]]["file_id"], file_stream)
                cleaned_doc["file_id"] = file_id
                supabase.table("scraped_articles").update(cleaned_doc).eq(
                    "id", docs["id"]
                ).execute()
                updated += 1
            except Exception as e:
                print(f"Error updating article {docs['id']}: {e}")
        else:
            # New scrape
            docs_add.append(docs)
            cleaned_doc = {
                "id": docs["id"],
                "hash": docs["hash"],
                "updated_at": docs["updated_at"],
            }
            try:
                file_streams = open(docs["file_path"], "rb")
                file_id = vector_store_service.upload_file(file_streams)
                cleaned_doc["file_id"] = file_id
                supabase.table("scraped_articles").insert(cleaned_doc).execute()
                added += 1
            except Exception as e:
                print(f"Error adding article {docs['id']}: {e}")

    # if docs_add:
    #     file_streams = [open(doc["file_path"], "rb") for doc in docs_add]
    #     file_batch = vector_store_service.upload_files(file_streams)
        

    print(f"Added: {len(docs_add)}, Updated: {len(docs_update)}, Skipped: {skipped}, Deleted: {deleted}")

    for file in new_files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"Error deleting file {file}: {e}")


if __name__ == "__main__":
    main()
