# FROM python:3.11-slim

# WORKDIR /app
# COPY . .

# RUN pip install --no-cache-dir -r requirements.txt

# ENTRYPOINT ["python"]

FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ENTRYPOINT stays optional; CMD gives flexibility
CMD ["python", "main.py"]
