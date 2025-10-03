# Use the optimized Uvicorn-Gunicorn-FastAPI base image
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Set the working directory (default is /app)
WORKDIR /app

# Install dependencies (this uses a caching layer for faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# The base image handles the CMD/ENTRYPOINT automatically,
# typically running the app from /app/main.py or /app/app/main.py.
# Ensure your main FastAPI file is named `main.py` in this directory.