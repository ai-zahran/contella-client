from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from azure.storage.blob import BlobServiceClient
from starlette.middleware import Middleware

import os
import uuid
import uvicorn


from src.validation import PDFUploadValidationMiddleware, \
    validate_and_normalize_email  # Import the middleware class, not an instance.


if os.path.exists(".env"):
    load_dotenv()

middleware = [
    Middleware(PDFUploadValidationMiddleware, max_size_mb=10, target_paths=["/upload-pdf/"])  # Set max size to 10 MB
]
app = FastAPI(middleware=middleware)
# app = FastAPI()

connect_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
cosmos_key = os.getenv("COSMOS_DB_KEY")
azure_storage_account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')

for v in [connect_str, cosmos_endpoint, cosmos_key, azure_storage_account_name]:
    assert isinstance(v, str) and v.strip() != ""

blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = "pdf-files"  # Define your container name

# Cosmos DB setup
cosmos_database_name = "pdf_data"
cosmos_container_name = "pdf_records"


# Initialize Cosmos DB client and create database/container if not exists
cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
database = cosmos_client.create_database_if_not_exists(id=cosmos_database_name)
container = database.create_container_if_not_exists(
    id=cosmos_container_name,
    partition_key=PartitionKey(path="/email"),
    offer_throughput=400
)


@app.post("/validate-email/")
async def add_email(email: str = Form(...)):
    try:
        is_email_valid, email_normalized = validate_and_normalize_email(email)
        return {"isValid": is_email_valid, "email": email_normalized}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-pdf/")
async def upload_pdf(email: str = Form(...), pdfFile: UploadFile = File(...)):
    # Check if the uploaded file is a PDF
    # pdfFile = email
    if pdfFile.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Generate a unique filename to prevent overwriting
    unique_filename = f"{uuid.uuid4()}_{pdfFile.filename}"

    try:
        # Create a blob client for the file
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=unique_filename)
        # Upload the file
        file_data = await pdfFile.read()
        blob_client.upload_blob(file_data)

        # Construct the PDF link
        pdf_link = f"https://{azure_storage_account_name}.blob.core.windows.net/" \
                   f"{container_name}/{unique_filename}"

        # Create a record to store in Cosmos DB
        pdf_record = {
            "id": str(uuid.uuid4()),  # Unique ID for Cosmos DB
            "email": email,
            "pdf_link": pdf_link
        }
        # Insert the record into Cosmos DB
        container.create_item(body=pdf_record)

        return {"message": "File uploaded successfully", "filename": pdfFile.filename, "pdf_link": pdf_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
