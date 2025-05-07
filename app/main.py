import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

from fastapi import FastAPI
from app.core.cors import setup_cors
from app.api.endpoints import router as api_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
setup_cors(app)

# Ensure static directories exist
os.makedirs("static/downloaded_images", exist_ok=True)
os.makedirs("static/reference_images", exist_ok=True)

# Mount static folders
app.mount("/downloaded_images", StaticFiles(directory="static/downloaded_images"), name="downloaded_images")
app.mount("/reference_images", StaticFiles(directory="static/reference_images"), name="reference_images")

# Include API routes
app.include_router(api_router)
