import os

async def save_uploaded_file(file, path):
    with open(path, "wb") as f:
        content = await file.read()
        f.write(content)

def clear_and_create(folder):
    import shutil
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)
