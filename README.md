# DocuMind AI

RAG-powered document query system with JWT authentication and semantic search.

## Features

- JWT authentication with bcrypt password hashing
- Rate limiting (10 req/min per user, 100 req/hour global)
- Groq LLM integration (llama-3.3-70b)
- ChromaDB vector search
- Document processing (PDF, DOCX, TXT)
- Real-time streaming responses
- Chat session management

## Tech Stack

FastAPI • MongoDB • ChromaDB • Groq API • SentenceTransformers

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` with your credentials:
```
MONGODB_URL=mongodb://localhost:27017
GROQ_API_KEY=your_key
JWT_SECRET_KEY=your_secret
```

Run:
```bash
uvicorn main:app --reload
```

API docs: `http://localhost:8000/api/docs`

## Deployment

Works on Render/Railway free tier. Set environment variables and deploy via `render.yaml` or `Procfile`.
