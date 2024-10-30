# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the code
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Expose port 80 for the API
EXPOSE 80

# Run the FastAPI application with Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
