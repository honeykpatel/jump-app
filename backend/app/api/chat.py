# backend/app/api/chat.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from openai import OpenAI
from backend.app.services.google import get_recent_emails, get_upcoming_events


router = APIRouter()

# Initialize OpenAI client
client = OpenAI()  # Reads from OPENAI_API_KEY env var

# Request schema
class ChatRequest(BaseModel):
    question: str

# Response schema
class ChatResponse(BaseModel):
    answer: str

def ask_openai(question: str, context: str = "") -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant for a financial advisor. "
                    "Use the provided Gmail and Google Calendar context to answer questions clearly and concisely. "
                    "Mention email subjects, sender names, and specific times or dates when available. "
                    "Respond in a professional tone."
                )
            },
            {
                "role": "user",
                "content": f"Recent Emails:\n{context}\n\nQuestion: {question}"
            }
        ]
    )
    return response.choices[0].message.content.strip()

@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    try:
        emails = get_recent_emails()
        events = get_upcoming_events()

        # Format emails and events
        formatted_emails = (
            "\n".join(f"- {email}" for email in emails) if isinstance(emails, list) else str(emails)
        )
        formatted_events = (
            "\n".join(f"- {event}" for event in events) if isinstance(events, list) else str(events)
        )

        context = (
            f"Recent emails:\n{formatted_emails}\n\n"
            f"Upcoming calendar events:\n{formatted_events}"
        )
        answer = ask_openai(request.question, context=context)
        return ChatResponse(answer=answer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
