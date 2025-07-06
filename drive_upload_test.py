import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def test_google_drive_upload():
    try:
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': 'BTCUSDT_TA_1h.csv',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }

        media = MediaFileUpload('BTCUSDT_TA_1h.csv', mimetype='text/csv')

        print("🚀 Uploading file to Google Drive...")
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name'
        ).execute()

        assert 'id' in uploaded_file
        assert uploaded_file['name'] == 'BTCUSDT_TA_1h.csv'

        # Optional: Share file
        service.permissions().create(
            fileId=uploaded_file['id'],
            body={
                'type': 'user',
                'role': 'writer',
                'emailAddress': 'dbrunson2011@gmail.com',
            },
            fields='id'
        ).execute()

        print(f"✅ Uploaded: {uploaded_file['name']} [ID: {uploaded_file['id']}]")
    except Exception as e:
        raise AssertionError(f"❌ Upload failed: {e}")
