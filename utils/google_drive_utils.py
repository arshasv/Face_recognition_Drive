from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """
    Authenticate and return a Google Drive service object.
    """
    creds = None

    # Check if token.json exists (stores user access and refresh tokens)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials are available, prompt the user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {str(e)}")
                creds = None
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json',
                    scopes=SCOPES,
                    redirect_uri='http://localhost:8000/'  # Explicitly set the redirect URI
                )
                creds = flow.run_local_server(port=8001)  # Use a fixed port
            except Exception as e:
                print(f"Error during OAuth flow: {str(e)}")
                return None

        # Save the credentials for future use
        try:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Error saving credentials to token.json: {str(e)}")

    # Build and return the Google Drive service
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Error building Google Drive service: {str(e)}")
        return None


def fetch_images_from_folder(folder_link):
    """
    Fetch all image files from a Google Drive folder.

    Args:
        folder_link (str): The shared link to the Google Drive folder.

    Returns:
        list: A list of dictionaries containing image names and URLs.
    """
    try:
        # Extract the folder ID from the shared link
        folder_id = folder_link.split('/')[-1]

        # Initialize the Google Drive service
        drive_service = get_drive_service()
        if not drive_service:
            print("Failed to initialize Google Drive service.")
            return []

        # Query the Google Drive API to list all image files in the folder
        results = drive_service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'image/'",
            fields="files(id, name, webViewLink)"
        ).execute()

        items = results.get('files', [])

        if not items:
            print("No images found in the specified Google Drive folder.")
            return []

        # Return the list of image URLs
        return [{"name": item['name'], "url": item['webViewLink']} for item in items]

    except Exception as e:
        print(f"Error fetching images from Google Drive: {str(e)}")
        return []