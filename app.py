import traceback
import os

# --- Disable GPU ---
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2" 
os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "false"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import shutil
import base64
import uuid
import re
from urllib.parse import urlparse, parse_qs
import requests

from fastapi import FastAPI, UploadFile, File, Form,  HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from deepface import DeepFace

# --- Disable GPU for PyTorch if present ---
import torch
torch.cuda.is_available = lambda : False

# --- Setup app ---
app = FastAPI()

# --- Setup folders ---
DOWNLOAD_FOLDER = "downloaded_images"
REFERENCE_FOLDER = "reference_images"

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(REFERENCE_FOLDER, exist_ok=True)

# --- Serve static files ---
app.mount("/downloaded_images", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloaded_images")
app.mount("/reference_images", StaticFiles(directory=REFERENCE_FOLDER), name="reference_images")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic models ---
class ImageURL(BaseModel):
    name: str
    url: str

class ScanRequest(BaseModel):
    referenceImage: str
    imageUrls: List[ImageURL]

# --- Helper functions ---
def extract_file_id_from_url(url: str) -> str:
    if "uc?id=" in url:
        return parse_qs(urlparse(url).query).get("id", [None])[0]
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

def download_images_from_google_drive(folder_id: str):
    from pydrive.auth import GoogleAuth
    from pydrive.drive import GoogleDrive

    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    query = f"'{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()

    image_paths = []

    for file in file_list:
        file_name = file['title']
        save_path = os.path.join(DOWNLOAD_FOLDER, file_name)
        print(f"Downloading {file_name} to {save_path}")
        try:
            file.GetContentFile(save_path)
            if os.path.exists(save_path):
                image_paths.append(save_path)
            else:
                print(f"Failed to save image: {file_name}")
        except Exception as e:
            print(f"Error downloading {file_name}: {e}")

    return image_paths

# --- API Endpoints ---

from fastapi import Request

@app.get("/fetch-images")
def fetch_images(folder_id: str, request: Request):
    try:
        if os.path.exists(DOWNLOAD_FOLDER):
            shutil.rmtree(DOWNLOAD_FOLDER)
        os.makedirs(DOWNLOAD_FOLDER)

        image_paths = download_images_from_google_drive(folder_id)

        base_url = str(request.base_url).rstrip("/")
        image_info = [
            {
                "name": os.path.basename(path),
                "url": f"{base_url}/downloaded_images/{os.path.basename(path)}"
            }
            for path in image_paths
        ]

        print(f"Fetched {len(image_info)} images.")
        return JSONResponse(content={"images": image_info})
    except Exception as e:
        print(f"Error in /fetch-images: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/upload-reference-image")
async def upload_reference_image(request: Request, file: UploadFile = File(...)):
    try:
        filename = f"ref_{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(REFERENCE_FOLDER, filename)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        full_url = f"{str(request.base_url).rstrip('/')}/reference_images/{filename}"
        return {
        "url": str(request.base_url) + f"reference_images/{filename}",
        "filename": filename
        } 
    except Exception as e:
        print(f"Error uploading reference image: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

    
@app.post("/scan")
async def scan_faces(reference_image: UploadFile = File(...), folder_link: str = Form(...)):
    try:
        print("Received scan request")
        print(f"Folder link: {folder_link}")
        print(f"Reference image: {reference_image.filename}")

        folder_id = extract_file_id_from_url(folder_link)
        image_paths = download_images_from_google_drive(folder_id)
        image_urls = [f"/downloaded_images/{os.path.basename(path)}" for path in image_paths]
        print(f"Fetched {len(image_urls)} image URLs from Google Drive")

        # Save reference image to local disk
        reference_path = f"temp/{reference_image.filename}"
        os.makedirs("temp", exist_ok=True)
        with open(reference_path, "wb") as f:
            f.write(await reference_image.read())
        print(f"Saved reference image to {reference_path}")

        matched_images = []

        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url)
                local_image_path = f"temp/image_{i}.jpg"
                with open(local_image_path, "wb") as f:
                    f.write(response.content)

                result = DeepFace.verify(
                    reference_path,
                    local_image_path,
                    model_name='SFace',
                    enforce_detection=False,
                    detector_backend='retinaface'
                )

                if result["verified"]:
                    matched_images.append(url)
            except Exception as e:
                print(f"Error verifying image {url}: {e}")

        return {"matched_images": matched_images}
    except Exception as e:
        print(f"Error in /scan endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to scan images")