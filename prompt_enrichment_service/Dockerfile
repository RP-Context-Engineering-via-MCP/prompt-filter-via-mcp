# Use a lightweight official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Copy the remaining source code
COPY . .

# Expose the API port
EXPOSE 3004

# Command to run uvicorn server directly
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3004"]
