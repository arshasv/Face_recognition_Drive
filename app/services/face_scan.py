import os
from app.utils.image_tools import is_valid_image
from app.services.google_drive_utils import download_images_from_google_drive

def scan_folder_for_face(folder_id: str, ref_image_path: str):
    # Lazy import inside the function to prevent early CUDA initialization
    from deepface import DeepFace

    matches = []
    image_paths = download_images_from_google_drive(folder_id)
    for path in image_paths:
        if not is_valid_image(path):
            continue
        try:
            result = DeepFace.verify(img1_path=ref_image_path, img2_path=path,
                                     model_name='SFace', enforce_detection=False,
                                     detector_backend='retinaface')
            if result.get("verified"):
                matches.append(f"/downloaded_images/{os.path.basename(path)}")
        except Exception as e:
            print(f"DeepFace error on {path}: {e}")
    return matches
