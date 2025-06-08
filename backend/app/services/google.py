import os
import pickle
import base64
from datetime import datetime

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly"
]

TOKEN_FILE = "token.pickle"
CREDENTIALS_FILE = "backend/app/credentials.json"

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds

def get_gmail_service():
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)

def get_calendar_service():
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)

def get_recent_emails(max_results=5):
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, q="is:inbox"
    ).execute()
    messages = results.get("messages", [])
    email_summaries = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "")
        date = next((h["value"] for h in headers if h["name"] == "Date"), "")

        # Get the body (plain text if available)
        body = ""
        parts = msg_data["payload"].get("parts", [])
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
        if not body:
            # Fallback to snippet
            body = msg_data.get("snippet", "")

        summary = (
            f"From: {sender}\n"
            f"Date: {date}\n"
            f"Subject: {subject}\n"
            f"Body: {body.strip()[:1000]}"  # truncate to 1000 chars to keep prompt short
        )
        email_summaries.append(summary)

    return "\n\n".join(f"Email #{i+1}:\n{email}" for i, email in enumerate(email_summaries))

def get_upcoming_events(max_results=5):
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    upcoming = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        upcoming.append(f"{event.get('summary', 'No Title')} at {start}")

    return upcoming

