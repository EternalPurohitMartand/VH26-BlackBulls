FROM python:3.11-slim

WORKDIR /app

# Copy the entire repository into the container
COPY . /app

# The CLI will be our main execution point
ENTRYPOINT ["python", "/app/cli.py"]