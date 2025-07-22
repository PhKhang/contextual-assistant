from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI()

LOGS_DIR = Path("/var/www/html/job_logs")

HTML_TEMPLATE = HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Job Logs</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Inter&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background: #f9f9f9;
            color: #333;
            padding: 2rem;
            max-width: 800px;
            margin: auto;
        }}
        h1, h2 {{
            text-align: center;
        }}
        pre {{
            font-family: 'JetBrains Mono', monospace;
            background: #272822;
            color: #f8f8f2;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
        }}
        ul {{
            list-style: none;
            padding: 0;
        }}
        li {{
            margin: 0.5rem 0;
        }}
        a {{
            text-decoration: none;
            color: #007acc;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Job Logs</h1>
    {content}
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def home():
    content = """
    <h2>Available Endpoints</h2>
    <ul>
        <li><a href="/latest">/latest</a> - Show latest log content</li>
        <li><a href="/logs">/logs</a> - List all log files</li>
    </ul>
    """
    return HTML_TEMPLATE.format(content=content)

@app.get("/latest", response_class=HTMLResponse)
async def latest_log():
    files = sorted(LOGS_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return HTML_TEMPLATE.format(content="<p>No log files found.</p>")
    latest_file = files[0]
    content = latest_file.read_text()
    html_content = f"""
    <h2>Latest log: {latest_file.name}</h2>
    <pre>{content}</pre>
    <p><a href="/logs">Back to all logs</a></p>
    """
    return HTML_TEMPLATE.format(content=html_content)

@app.get("/logs", response_class=HTMLResponse)
async def list_logs():
    files = sorted(LOGS_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return HTML_TEMPLATE.format(content="<p>No log files found.</p>")
    links = "\n".join(f'<li><a href="/log/{f.name}">{f.name}</a></li>' for f in files)
    html_content = f"""
    <h2>All Logs</h2>
    <ul>{links}</ul>
    <p><a href="/latest">View latest log</a></p>
    """
    return HTML_TEMPLATE.format(content=html_content)

@app.get("/log/{log_name}", response_class=HTMLResponse)
async def show_log(log_name: str):
    file_path = LOGS_DIR / log_name
    if not file_path.exists():
        return HTML_TEMPLATE.format(content=f"<p>Log file {log_name} not found.</p>")
    content = file_path.read_text()
    html_content = f"""
    <h2>Log: {log_name}</h2>
    <pre>{content}</pre>
    <p><a href="/logs">Back to all logs</a></p>
    """
    return HTML_TEMPLATE.format(content=html_content)
