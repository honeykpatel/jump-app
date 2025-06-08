from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from backend.app.api import auth, chat
from backend.app.services.google import build_flow, handle_google_callback
from dotenv import load_dotenv
import os
import secrets
import pickle

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth flow
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "supersecret"))

# Register API routers
app.include_router(auth.router, prefix="/auth")
app.include_router(chat.router, prefix="/chat")

@app.get("/")
def root():
    return {"status": "Backend is running"}

@app.get("/auth/google/login")
async def google_login(request: Request):
    # Build flow and store in session
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    request.session["google_oauth_flow"] = pickle.dumps(flow).decode("latin1")
    return RedirectResponse(auth_url)

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse("Missing code in callback", status_code=400)
    try:
        handle_google_callback(request, code)
        return HTMLResponse("✅ Google OAuth successful! You can now access calendar/email APIs.")
    except Exception as e:
        return HTMLResponse(f"❌ OAuth failed: {e}", status_code=500)
