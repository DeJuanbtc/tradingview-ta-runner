from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Auth and API setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# File metadata
file_metadata = {
    'name': 'BTCUSDT_TA_1h.csv',
    'mimeType': 'application/vnd.google-apps.spreadsheet'
}
media = MediaFileUpload('BTCUSDT_TA_1h.csv', mimetype='text/csv')

# Upload and share
try:
    print("🚀 Uploading file to Google Drive...")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name'
    ).execute()

    # Share with your Gmail so it appears in Drive
    service.permissions().create(
        fileId=file.get('id'),
        body={
            'type': 'user',
            'role': 'writer',
            'emailAddress': 'dbrunson2011@gmail.com'
        },
        fields='id'
    ).execute()

    print(f"✅ Uploaded: ID={file.get('id')} | Name={file.get('name')}")
    print(f"🔗 Access it at: https://drive.google.com/file/d/{file.get('id')}/view")
except Exception as e:
    print(f"❌ Upload failed: {e}")
