import os
import shutil
import base64
import uuid
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from deepface import DeepFace
import re
from urllib.parse import urlparse, parse_qs

app = FastAPI()

DOWNLOAD_FOLDER = "downloaded_images"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app.mount("/downloaded_images", StaticFiles(directory=DOWNLOAD_FOLDER), name="downloaded_images")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ImageURL(BaseModel):
    name: str
    url: str

class ScanRequest(BaseModel):
    referenceImage: str
    imageUrls: List[ImageURL]

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

@app.get("/fetch-images")
def fetch_images(folder_id: str):
    try:
        if os.path.exists(DOWNLOAD_FOLDER):
            shutil.rmtree(DOWNLOAD_FOLDER)
        os.makedirs(DOWNLOAD_FOLDER)

        image_paths = download_images_from_google_drive(folder_id)

        image_info = [
            {
                "name": os.path.basename(path),
                "url": f"/downloaded_images/{os.path.basename(path)}"
            }
            for path in image_paths
        ]

        print(f"Fetched {len(image_info)} images.")
        return JSONResponse(content={"images": image_info})
    except Exception as e:
        print(f"Error in /fetch-images: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/scan")
def scan_faces(request: ScanRequest):
    matched_images = []

    reference_path = f"ref_{uuid.uuid4().hex}.jpg"
    with open(reference_path, "wb") as f:
        f.write(base64.b64decode(request.referenceImage.split(",")[-1]))

    for img in request.imageUrls:
        try:
            # Handle URLs like: http://localhost:8000/downloaded_images/AKR04897.jpg
            parsed = urlparse(img.url)
            file_name = os.path.basename(parsed.path)

            # Optional fallback if filename is passed in query string (unlikely now)
            if not file_name:
                qs = parse_qs(parsed.query)
                file_name = qs.get("id", [None])[0]

            local_image_path = os.path.join(DOWNLOAD_FOLDER, file_name)

            if not os.path.exists(local_image_path):
                print(f"File not found: {local_image_path}")
                continue

            result = DeepFace.verify(reference_path, local_image_path, enforce_detection=False)
            if result.get("verified"):
                matched_images.append(img)

        except Exception as e:
            print(f"Error verifying {img.name}: {e}")

    os.remove(reference_path)