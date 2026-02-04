# Infrastructure: Docker & Docker Compose

**Status**: Backlog
**ID**: task-006

## Description
Currently, the application runs directly on the host using a virtual environment (`venv`). This requires manual installation of system dependencies (like `ffmpeg`) and depends on the specific Python version installed on the OS. Dockerizing the application will ensure a consistent environment across development, testing, and production.

## Goals
1.  Create a `Dockerfile`:
    -   Use a lightweight base image (e.g., `python:3.12-slim`).
    -   Install necessary system dependencies (`ffmpeg`, `gcc` if needed for compilation).
    -   Install Python dependencies via `pip`.
    -   Set up a non-root user for security.
2.  Create `docker-compose.yml`:
    -   Define the `tg-translator` service.
    -   Map necessary volumes (e.g., for logs or persistent database/dictionaries).
    -   Pass environment variables (`.env`).
3.  Update `Makefile`:
    -   Add commands for building and running containers (e.g., `make docker-build`, `make docker-up`).
4.  Verify local execution works identically to the `venv` setup.

## Benefits
-   **Reproducibility**: Eliminates "works on my machine" issues.
-   **Deployment**: Simplifies deployment (just `docker compose up -d` on the server).
-   **Isolation**: Separation from host system libraries.

## Technical Details
-   Ensure `ffmpeg` is installed in the container image as it is required for audio processing (Ogg -> Wav conversion).
-   Persist the `db.sqlite` (if used) via Docker volumes to avoid data loss on container recreation.