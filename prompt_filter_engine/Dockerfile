# Use a lightweight official Python image
FROM python:3.10-slim

# Set working directory to the parent /app workspace so the module 'prompt_filter_engine' can be resolved
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# Copy the source code into the prompt_filter_engine directory so it aligns with Python package name
COPY . /app/prompt_filter_engine

# Expose the API port
EXPOSE 3003

# Command to run the application using module syntax to ensure proper resolution
CMD ["python", "-m", "prompt_filter_engine.server"]
