# backend/app/api/auth.py
import sys
sys.path.append("..")
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import urllib.parse
from backend.app import config
from backend.app.services.google import build_flow
import pickle
router = APIRouter()

# === GOOGLE OAUTH FLOW ===
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

@router.get("/google")
def google_auth():
    params = {
        "client_id": config.settings.GOOGLE_CLIENT_ID,
        "redirect_uri": config.settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent"
    }
    url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@router.get("/google/login")
async def google_login(request: Request):
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    request.session["google_oauth_state"] = state  # Only store state
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(request: Request, code: str):
    state = request.session.get("google_oauth_state")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    flow = build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # ✅ Save token.pickle
    with open("token.pickle", "wb") as token_file:
        pickle.dump(credentials, token_file)

    return HTMLResponse("✅ Google OAuth successful! Token saved.")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return HTMLResponse("✅ Logged out successfully.")



# === HUBSPOT OAUTH FLOW ===
HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_SCOPES = "contacts crm.objects.contacts.read crm.objects.contacts.write"

@router.get("/hubspot")
def hubspot_auth():
    params = {
        "client_id": config.settings.HUBSPOT_CLIENT_ID,
        "redirect_uri": config.settings.HUBSPOT_REDIRECT_URI,
        "scope": HUBSPOT_SCOPES,
        "response_type": "code"
    }
    url = HUBSPOT_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)

@router.get("/hubspot/callback")
async def hubspot_callback(code: str):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "client_id": config.settings.HUBSPOT_CLIENT_ID,
        "client_secret": config.settings.HUBSPOT_CLIENT_SECRET,
        "redirect_uri": config.settings.HUBSPOT_REDIRECT_URI,
        "code": code
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(HUBSPOT_TOKEN_URL, headers=headers, data=data)
        token_data = resp.json()
        return token_data
