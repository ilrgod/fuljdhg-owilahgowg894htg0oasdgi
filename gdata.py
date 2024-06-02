import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


class GoogleDriveManager:
    def __init__(self, credentials_json):
        self.credentials = service_account.Credentials.from_service_account_file(credentials_json)
        self.service = build('drive', 'v3', credentials=self.credentials)

    def upload_photo(self, file_name, file_bytes, mime_type):
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
        file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        self.service.permissions().create(
            fileId=file.get('id'),
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        return file.get('id')

    def get_photo_link(self, file_id):
        file = self.service.files().get(fileId=file_id, fields='webContentLink').execute()
        return file.get('webContentLink')
