from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
from supabase import Client, create_client
from services.api_service import fetch_articles, save_article_as_md
from services.vector_store_service import VectorStoreService
from utils.file_utils import get_files_in_directory, get_hash_from_files

load_dotenv()

OUTPUT_DIR = "articles_md"

def main():
    print("Fetching articles...")
    articles = fetch_articles()
    print(f"Total articles fetched: {len(articles)}")

    for article in articles:
        save_article_as_md(article)

    print(f"Saved all Markdown files in '{OUTPUT_DIR}' folder.")

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    response = (
        supabase.table("scraped_articles")
        .select("hash", "updated_at", "id", "file_id")
        .execute()
    )
    old_hashes = set(item["hash"] for item in response.data)
    old_ids = set(str(item["id"]) for item in response.data)

    new_files = get_files_in_directory(OUTPUT_DIR)
    new_hashes = get_hash_from_files(new_files)

    new_ids = set(file.split(os.sep)[-1].split("_")[0] for file in new_files)

    deleted_ids = old_ids - new_ids
    print(
        f"New files: {len(new_files)}, Old files: {len(old_ids)}, Deleted files: {len(deleted_ids)}"
    )

    print("Creating old documents dictionary...")
    old_docs = {
        str(item["id"]): {
            "id": item["id"],
            "hash": item["hash"],
            "updated_at": item["updated_at"],
            "file_id": item["file_id"],
        }
        for item in response.data
    }

    print("Processing new documents...")
    new_docs = [
        {
            "id": file.split(os.sep)[-1].split("_")[0],
            "hash": hash_value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "file_path": file,
        }
        for file, hash_value in zip(new_files, new_hashes)
    ]

    print("Connecting to Vector Store Service...")
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    vector_store_id = os.environ.get("VECTOR_STORE_ID")

    vector_store_service = VectorStoreService(
        client=client, vector_store_id=vector_store_id
    )

    added = 0
    updated = 0
    skipped = 0
    deleted = 0
    
    if deleted_ids:
        print(f"Deleting {len(deleted_ids)} old articles...")
    for doc_id in deleted_ids:
        result = (
            supabase.table("scraped_articles")
            .delete(returning="representation")
            .eq("id", doc_id)
            .execute()
        )
        vector_store_service.delete_file(result.data[0]["file_id"])
        deleted += 1

    print("Check new documents against old documents...")
    for doc in tqdm(new_docs):
        if doc["hash"] in old_hashes:
            # Old scrape
            skipped += 1
        elif doc["id"] in old_docs:
            # Update scrape
            cleaned_doc = {
                "id": doc["id"],
                "hash": doc["hash"],
                "updated_at": doc["updated_at"],
            }
            try:
                file_stream = open(doc["file_path"], "rb")
                file_id = vector_store_service.update_file(
                    old_docs[doc["id"]]["file_id"], file_stream
                )
                cleaned_doc["file_id"] = file_id
                supabase.table("scraped_articles").update(cleaned_doc).eq(
                    "id", doc["id"]
                ).execute()
                updated += 1
            except Exception as e:
                print(f"Error updating article {doc['id']}: {e}")
        else:
            # New scrape
            cleaned_doc = {
                "id": doc["id"],
                "hash": doc["hash"],
                "updated_at": doc["updated_at"],
            }
            try:
                file_streams = open(doc["file_path"], "rb")
                file_id = vector_store_service.upload_file(file_streams)
                cleaned_doc["file_id"] = file_id
                supabase.table("scraped_articles").insert(cleaned_doc).execute()
                added += 1
            except Exception as e:
                print(f"Error adding article {doc['id']}: {e}")

    print(
        f"Added: {added}, Updated: {updated}, Skipped: {skipped}, Deleted: {deleted}"
    )

    print("Cleaning up old files...")
    for file in new_files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"Error deleting file {file}: {e}")


if __name__ == "__main__":
    main()
