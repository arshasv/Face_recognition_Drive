from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from app.api.models import ImageURL, ScanRequest
from app.services.google_drive_utils import download_images_from_google_drive
from app.services.face_scan import scan_folder_for_face
from app.utils.file_utils import save_uploaded_file, clear_and_create
from app.utils.image_tools import is_valid_image
import os
import uuid

router = APIRouter()

DOWNLOAD_FOLDER = "static/downloaded_images"
REFERENCE_FOLDER = "static/reference_images"

@router.get("/fetch-images")
def fetch_images(folder_id: str, request: Request):
    try:
        clear_and_create(DOWNLOAD_FOLDER)
        image_paths = download_images_from_google_drive(folder_id)
        base_url = str(request.base_url).rstrip("/")
        image_info = [
            {"name": os.path.basename(p), "url": f"{base_url}/downloaded_images/{os.path.basename(p)}"}
            for p in image_paths
        ]
        return {"images": image_info}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/upload-reference-image")
async def upload_reference_image(request: Request, file: UploadFile = File(...)):
    try:
        filename = f"ref_{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(REFERENCE_FOLDER, filename)
        await save_uploaded_file(file, file_path)
        url = f"{str(request.base_url).rstrip('/')}/reference_images/{filename}"
        return {"url": url, "filename": filename}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/scan")
async def scan_faces(reference_image: UploadFile = File(...), folder_link: str = Form(...)):
    try:
        filename = f"temp/{uuid.uuid4().hex}_{reference_image.filename}"
        os.makedirs("temp", exist_ok=True)
        await save_uploaded_file(reference_image, filename)

        if not is_valid_image(filename):
            raise HTTPException(status_code=400, detail="Invalid reference image")

        matches = scan_folder_for_face(folder_link, filename)
        return {"matched_images": matches}
    except Exception as e:
        print(f"Error in scan_faces: {str(e)}")  # Log the error
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))