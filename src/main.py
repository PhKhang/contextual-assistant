from datetime import datetime, timezone
import hashlib
import os
from dotenv import load_dotenv
from supabase import Client, create_client
from services.api_service import fetch_articles, save_article_as_md

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
    # print("Fetching articles...")
    # articles = fetch_articles()
    # print(f"Total articles fetched: {len(articles)}")

    # for article in articles:
    #     save_article_as_md(article)

    # print(f"Saved all Markdown files in '{OUTPUT_DIR}' folder.")

    added = 0
    updated = 0
    skipped = 0
    deleted = 0

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    response = (
        supabase.table("scraped_articles").select("hash", "updated_at", "id").execute()
    )
    old_data = {item["id"]: item for item in response.data}
    old_hashes = set(item["hash"] for item in response.data)
    old_ids = set(str(key) for key in old_data.keys())

    new_files = get_files_in_directory(OUTPUT_DIR)
    new_hashes = get_hash_from_files(new_files)
    
    new_ids = set(file.split(os.sep)[-1].split("_")[0] for file in new_files)
    print(len(new_files))
    print(len(new_ids))
    # return
    
    deleted_ids = old_ids - new_ids
    print(f"Old IDs: {len(old_ids)}, New IDs: {len(new_ids)}")
    print(f"Deleted IDs: {len(deleted_ids)}")
    # for d_id in deleted_ids:
    #     for id in new_ids:
    #         if d_id == id:
    #             print(f"Error: Deleted ID {d_id} found in new IDs, something went wrong.")


    old_docs = {
        item["id"]: {
            "hash": item["hash"],
            "updated_at": item["updated_at"],
        }
        for item in response.data
    }

    new_docs = [
        {
            "id": file.split(os.sep)[-1].split("_")[0],
            "hash": hash_value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        for file, hash_value in zip(new_files, new_hashes)
    ]
    print(len(new_docs))
    # return
            
    for doc_id in deleted_ids:
        deleted += 1
        supabase.table("scraped_articles").delete().eq("id", doc_id).execute()
    
    for docs in new_docs:
        if docs["hash"] in old_hashes:
            # Old scrape
            skipped += 1
        elif docs["id"] in old_docs:
            # Update scrape
            updated += 1
            supabase.table("scraped_articles").update(docs).eq("id", docs["id"]).execute()
        else:
            # New scrape
            added += 1
            supabase.table("scraped_articles").insert(docs).execute()

    print(f"Added: {added}, Updated: {updated}, Skipped: {skipped}, Deleted: {deleted}")
    
    for file in new_files:
        try:
            os.remove(file)
        except Exception as e:
            print(f"Error deleting file {file}: {e}")


if __name__ == "__main__":
    main()
