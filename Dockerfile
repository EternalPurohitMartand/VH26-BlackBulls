FROM python:3.11-slim

WORKDIR /app

# Copy the entire repository into the container
COPY . /app

# Install the ML dependencies
RUN pip install pandas scikit-learn joblib google-genai

# The CLI will be our main execution point
ENTRYPOINT ["python", "/app/cli.py"]