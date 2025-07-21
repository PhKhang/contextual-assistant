from urllib.parse import urlparse

def slugify(url) -> str:
    """
    Convert a URL to a slug with the last part as the fill name.
    
    Args:
        url (str): The URL to convert.
    Returns:
        str: A slugified version of the URL.
    """
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    return slug.replace("-", "_")