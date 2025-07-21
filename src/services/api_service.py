import os
import requests
from markdownify import markdownify as md
from utils.string_utils import slugify


BASE_URL = "https://support.optisigns.com/api/v2/help_center/articles.json"
OUTPUT_DIR = "articles_md"

def api_request(url) -> dict:
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

def extract_articles(data) -> tuple:
    if not data or "articles" not in data:
        return [], None
    
    articles = data.get("articles", [])
    next_page_url = data.get("next_page", None)
    return articles, next_page_url

def fetch_articles() -> list:
    all_articles = []
    url = BASE_URL
    
    while url:
        data = api_request(url)
        if not data:
            break
        
        article, next_page_url = extract_articles(data)
        all_articles.extend(article)
        url = next_page_url
        
    return all_articles

def save_article_as_md(article):
    try:
        html_content = article.get("body", "")
        markdown_content = md(html_content)
        
        slug = slugify(article.get("html_url", article["id"]))
        filename = os.path.join(OUTPUT_DIR, f"{slug}.md")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {article.get('title')}\n\n")
            f.write(markdown_content)
    except Exception as e:
        print(f"Error saving article {article.get('id', 'unknown')}: {e}")
        
