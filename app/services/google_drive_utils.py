from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

def download_images_from_google_drive(folder_id: str):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    query = f"'{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    image_paths = []

    os.makedirs("static/downloaded_images", exist_ok=True)

    for file in file_list:
        path = os.path.join("static/downloaded_images", file['title'])
        try:
            file.GetContentFile(path)
            image_paths.append(path)
        except Exception as e:
            print(f"Download error: {e}")

    return image_paths