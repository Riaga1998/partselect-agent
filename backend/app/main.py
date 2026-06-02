"""
FastAPI server — the bridge between the React frontend and the agent loop.

One endpoint: POST /chat
Receives the conversation history, runs the agent, returns the response.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import run_agent

app = FastAPI(title="PartSelect Agent API")

# Allow the React dev server (localhost:3000) to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str      # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class ChatResponse(BaseModel):
    role: str
    content: str
    tool_calls: list = []
    suggestions: list[str] = []


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    # Convert to the plain dicts the agent expects
    conversation = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        result = run_agent(conversation)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}
