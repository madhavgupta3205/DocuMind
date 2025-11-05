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

## Prerequisites

- Python 3.9+
- MongoDB (local or MongoDB Atlas)
- Groq API key (free from https://console.groq.com)

## Quick Start

1. Clone and setup:
```bash
git clone https://github.com/madhavgupta3205/DocuMind.git
cd DocuMind
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
```

Edit `.env`:
```env
MONGODB_URL=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key_here
JWT_SECRET_KEY=your_secret_key_here
```

3. Start MongoDB (if running locally):
```bash
mongod
```

4. Run the application:
```bash
uvicorn main:app --reload
```

5. Access API docs: `http://localhost:8000/api/docs`

## Project Structure

```
app/
├── routes/          # API endpoints
├── services/        # Business logic (LLM, DB, Vector)
├── models/          # Pydantic models
├── middleware/      # Auth middleware
└── utils/           # Helper functions
```
