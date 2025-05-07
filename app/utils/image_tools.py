import cv2
from PIL import Image

def is_valid_image(img_path):
    try:
        img = cv2.imread(img_path)
        if img is None or img.shape[0] < 50 or img.shape[1] < 50:
            return False
        with Image.open(img_path) as im:
            im.verify()
        return True
    except:
        return False