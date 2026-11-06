# SupportIQ AI

SupportIQ AI is an enterprise IT support assistant built with FastAPI and a LangGraph-based RAG workflow. It helps employees answer IT-related questions using a private knowledge base and can fall back to public web search when local documents are not enough.

## Overview

This project is designed for internal support use cases such as:

- VPN access and troubleshooting
- password reset guidance
- MFA and identity help
- laptop or device onboarding
- software access requests
- company policy and knowledge lookup
- general IT support questions

The application includes:

- a chatbot UI for internal staff
- document upload and ingestion support
- private-vector retrieval using Pinecone
- web fallback search using Tavily
- a LangGraph workflow for routing and evidence grading
- analytics and audit tracking for query performance

## Main Features

- Agentic RAG workflow for IT support questions
- Private knowledge-base search using Pinecone vectors
- External web fallback when local evidence is weak
- Upload support for PDF, TXT, MD, and DOCX files
- Admin-protected ingestion endpoint
- Dashboard UI with chat, document library, and analytics pages
- Audit tracking for queries, response time, retries, and success rates

## Tech Stack

- Python 3.13
- FastAPI
- Uvicorn
- Jinja2
- LangGraph
- LangChain Core / Community / OpenAI
- OpenRouter
- Pinecone
- Tavily
- SQLite for audit analytics

## Project Structure

```text
supportiq-ai/
├── app/
│   ├── api/
│   ├── core/
│   ├── rag/
│   └── services/
├── data/
│   └── sample_kb/
├── static/
│   ├── css/
│   └── js/
├── templates/
├── uploads/
├── tests/
├── .env
├── .gitignore
├── ingest_sample_kb.py
├── pyvenv.cfg
├── requirements.txt
├── run.py
├── README.md
└── .venv/   (local only, not committed)
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.13 or newer
- pip
- internet access for package installation and external API calls
- a Pinecone account
- an OpenRouter account
- a Tavily account

## Installation

1. Clone the repository:

```bash
git clone <your-repository-url>
cd supportiq-ai
```

2. Create a virtual environment:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Create a local environment file:

Create a file named `.env` in the project root and add your secrets.

## Required Environment Variables

The project loads values from `.env` automatically via `pydantic-settings`.

Example:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
TAVILY_API_KEY=your_tavily_api_key
PINECONE_API_KEY=your_pinecone_api_key
ADMIN_API_KEY=your_secure_admin_key

PINECONE_INDEX_NAME=supportiq-embedding-1536
PINECONE_NAMESPACE=company-it-kb
EMBEDDING_MODEL=openai/text-embedding-3-small
OPENROUTER_MODEL=recursive/flint-v1.0:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
APP_ENV=development
```

### Where to get each key

- OpenRouter API key
  - Go to https://openrouter.ai
  - Sign up or log in
  - Create an API key from your account dashboard

- Tavily API key
  - Go to https://app.tavily.com
  - Create an account and generate a key

- Pinecone API key
  - Go to https://app.pinecone.io
  - Create or open a project
  - Create an index and copy the API key

- Admin API key
  - Use a secure random string for the upload-protection header
  - This is sent in the `X-ADMIN-KEY` header when uploading files

> Important: do not commit `.env` to GitHub. It contains secrets and should stay local.

## Pinecone Setup Notes

This app expects a Pinecone index that matches the configured embedding model.

The default configuration uses:

- model: `openai/text-embedding-3-small`
- embedding dimension: `1536`
- index name: `supportiq-embedding-1536`
- namespace: `company-it-kb`

If you change the embedding model, make sure the Pinecone index dimension matches it.

## How to Run the Project

### 1. Index the sample knowledge base

```bash
python ingest_sample_kb.py
```

This loads the files from `data/sample_kb` and stores them into Pinecone for retrieval.

### 2. Start the FastAPI app

```bash
python run.py
```

This starts the app at:

```text
http://127.0.0.1:8000
```

You can also run the app manually:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Application Features in the UI

The web dashboard includes several views:

- Dashboard overview
- AI Assistant chat interface
- Uploaded data / document library
- Analytics dashboard
- Settings or workspace status area

The frontend reads from the API to show:

- the interaction trace from the LangGraph workflow
- selected source (`private_kb`, `web`, or `direct`)
- uploaded document metadata
- response-time and usage analytics

## API Endpoints

### Health check

```http
GET /api/health
```

### Ask a question

```http
POST /api/chat
```

Example request:

```json
{
  "question": "How do I reset my VPN password?"
}
```

### List documents

```http
GET /api/documents
```

### Get analytics

```http
GET /api/analytics?days=30
```

### Upload a document

```http
POST /api/ingest
```

Headers:

```http
X-ADMIN-KEY: your-admin-key
```

Supported file types:

- `.pdf`
- `.txt`
- `.md`
- `.docx`

## Supported File Types

The ingestion pipeline supports:

- `.pdf`
- `.txt`
- `.md`
- `.docx`

## GitHub Safety

Before pushing this project to GitHub, make sure:

1. `.env` is ignored
2. no real API keys are committed
3. your `uploads` folder does not contain sensitive documents
4. generated local files such as SQLite DBs remain out of version control

## `.gitignore`

This project should keep entries like the following:

```gitignore
.env
.env.*
.venv/
venv/
__pycache__/
*.pyc
uploads/*
!uploads/.gitkeep
*.db
*.sqlite3
```

## Notes

- This project is intended primarily for local development and internal deployment testing.
- The app reads local files and stores uploaded documents in the configured upload directory.
- Pinecone index existence and correct vector dimensions are required for successful retrieval.
- The analytics database is stored locally in the project data folder and should not be committed if it contains production data.

## License

This project does not currently include a formal license file. If you plan to publish it publicly on GitHub, add a license such as MIT or Apache-2.0.

## Support

If the project does not run correctly, verify:

- `.env` exists in the project root
- your API keys are valid
- your Pinecone index is created and has the correct dimension
- the sample knowledge base has been indexed
- the admin upload header matches your configured `ADMIN_API_KEY`
