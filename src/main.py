from datetime import datetime, timedelta, timezone
import os
import logging
from openai import OpenAI
from supabase import Client, create_client
from services.api_service import fetch_articles, save_article_as_md
from services.vector_store_service import VectorStoreService
from utils.file_utils import get_files_in_directory, get_hash_from_files
from core.config import settings

LOG_DIR = "job_logs"
os.makedirs(LOG_DIR, exist_ok=True)

now = datetime.now(timezone.utc) + timedelta(hours=7)

log_filename = f"job_log_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
log_path = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Disable OpenAI debug logging
os.environ.pop("OPENAI_LOG", None)

# Suppress logs from OpenAI, Supabase, httpx, urllib3
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

OUTPUT_DIR = "articles_md"


def main():
    logging.info("=============================================")
    logging.info(f"Job run: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=============================================")
    print("Log:", log_filename)

    print("Fetching articles...")
    logging.info("Fetching articles...")
    articles = fetch_articles()
    print(f"Total articles fetched: {len(articles)}")
    logging.info(f"Total articles fetched: {len(articles)}")

    logging.info("Saving articles as Markdown files...")
    for article in articles:
        save_article_as_md(article)

    logging.info("Saved all Markdown files")
    print(f"Saved all Markdown files in '{OUTPUT_DIR}' folder.")

    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

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
    logging.info("Connecting to Vector Store Service...")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    vector_store_id = settings.VECTOR_STORE_ID

    vector_store_service = VectorStoreService(
        client=client, vector_store_id=vector_store_id
    )
    logging.info("Vector Store Service setup completed.")

    added = 0
    updated = 0
    skipped = 0
    deleted = 0

    adding_files = []
    updating_files = []

    print("Check new documents against old documents...")
    logging.info("Check new documents against old documents...")
    # return
    for doc in new_docs:
        if doc["hash"] in old_hashes:
            # Old scrape
            skipped += 1
        elif doc["id"] in old_docs:
            # Update scrape
            updating_files.append(doc)
        else:
            # New scrape
            adding_files.append(doc)

    print(f"About to process {len(updating_files)} updates, {len(adding_files)} additions and {len(deleted_ids)} deletions.")
    logging.info(
        f"About to process {len(updating_files)} updates, {len(adding_files)} additions and {len(deleted_ids)} deletions."
    )

    modify = True
    if modify:
        # Update loop
        for doc in updating_files:
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
        logging.info(f"Updated {updated} articles.")
                
        # Add loop
        for doc in adding_files:
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
        logging.info(f"Added {added} articles.")
                
        # Delete loop
        for doc_id in deleted_ids:
            result = (
                supabase.table("scraped_articles")
                .delete(returning="representation")
                .eq("id", doc_id)
                .execute()
            )
            vector_store_service.delete_file(result.data[0]["file_id"])
            deleted += 1
        logging.info(f"Deleted {deleted} articles.")

    print(f"Added: {added}, Updated: {updated}, Skipped: {skipped}, Deleted: {deleted}")
    logging.info(
        f"Added: {added}, Updated: {updated}, Skipped: {skipped}, Deleted: {deleted}"
    )

    print("Cleaning up old files...")
    for file in new_files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"Error deleting file {file}: {e}")

    logging.info("Old files cleaned up.")
    logging.info("Job completed successfully.")


if __name__ == "__main__":
    main()
