# SupportIQ AI

SupportIQ AI is a FastAPI-based enterprise IT support assistant powered by a Retrieval-Augmented Generation (RAG) workflow. It indexes internal documents, answers employee questions using a private knowledge base, and falls back to web search when the local knowledge is insufficient.

## Overview

This project is designed for internal IT support use cases such as:

- password reset guidance
- VPN and MFA troubleshooting
- laptop and device setup
- access requests and software onboarding
- company IT policy questions
- general tech support queries

The system combines:

- FastAPI for the API and web UI
- LangGraph for the reasoning workflow
- LangChain + OpenRouter for LLM orchestration
- Pinecone for vector search
- Tavily for web fallback search
- Local document ingestion for PDF, TXT, MD, and DOCX files

## Tech Stack

- Python 3.13 (project environment is configured for Python 3.13)
- FastAPI
- Uvicorn
- LangGraph
- LangChain Core / Community / OpenAI
- Pinecone
- OpenRouter
- Tavily
- Jinja2

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
├── templates/
├── uploads/
├── .env
├── .gitignore
├── ingest_sample_kb.py
├── pyvenv.cfg
├── requirements.txt
├── run.py
├── README.md
└── tests/
```

## Prerequisites

Before running the project, make sure you have:

- Python 3.10 or later (3.13 is the version used in this project)
- pip
- access to the internet for package installation and external API calls
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

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

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

## Required API Keys and Where to Get Them

The application reads environment variables from `.env` using `pydantic-settings`.

Add values like this in `.env`:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
TAVILY_API_KEY=your_tavily_api_key
PINECONE_API_KEY=your_pinecone_api_key
ADMIN_API_KEY=change-this-to-a-secure-random-string

PINECONE_INDEX_NAME=supportiq-embedding-1536
PINECONE_NAMESPACE=company-it-kb
EMBEDDING_MODEL=openai/text-embedding-3-small
OPENROUTER_MODEL=recursive/flint-v1.0:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### Where to get each key

- OpenRouter API key:
  - Visit https://openrouter.ai
  - Sign up or log in
  - Create an API key from your dashboard

- Tavily API key:
  - Visit https://app.tavily.com
  - Create an account and generate a key

- Pinecone API key:
  - Visit https://app.pinecone.io
  - Create a project and an index
  - Copy the API key and set the index name in `.env`

- Admin API key:
  - Choose any secure random string for protecting the upload endpoint
  - This is used in the `X-ADMIN-KEY` header when uploading knowledge files

> Important: never commit your `.env` file to GitHub. It contains secrets and should stay on your local machine.

## Environment Variables Used by the App

These are the main variables the app expects:

- `OPENROUTER_API_KEY`
- `TAVILY_API_KEY`
- `PINECONE_API_KEY`
- `ADMIN_API_KEY`
- `PINECONE_INDEX_NAME`
- `PINECONE_NAMESPACE`
- `EMBEDDING_MODEL`
- `OPENROUTER_MODEL`
- `OPENROUTER_BASE_URL`

## Running the Project

### 1. Index the sample knowledge base

```bash
python ingest_sample_kb.py
```

This reads the files in `data/sample_kb` and pushes them into Pinecone for retrieval.

### 2. Start the FastAPI app

```bash
python run.py
```

The app will start on:

```text
http://127.0.0.1:8000
```

You can also run it manually with Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Accessing the App

Open this in your browser:

```text
http://127.0.0.1:8000/
```

The web interface includes a simple IT support chatbot UI.

## API Endpoints

### Health check

```http
GET /api/health
```

### Chat

```http
POST /api/chat
```

Request body:

```json
{
  "question": "How do I reset my VPN password?"
}
```

### Upload knowledge files

```http
POST /api/ingest
```

Headers:

```http
X-ADMIN-KEY: your-admin-key
```

This endpoint accepts PDF, TXT, MD, and DOCX files and stores them in the upload directory before indexing them.

## Supported Document Types

- `.pdf`
- `.txt`
- `.md`
- `.docx`

## Recommended GitHub Setup

Before pushing to GitHub:

1. Ensure `.env` is added to `.gitignore`
2. Do not commit real API keys or secrets
3. Keep the repository clean and provide public-safe configuration examples only

## .gitignore

This project should include entries similar to:

```gitignore
.env
.env.*
.venv/
venv/
__pycache__/
*.pyc
*.pyo
.DS_Store
uploads/*
!uploads/.gitkeep
```

## Notes

- The project is mainly intended for local development and testing before deployment.
- You should configure production-grade secrets and deployment settings before hosting publicly.
- Pinecone index creation and vector dimension matching are required for successful embedding and retrieval.

## License

This project does not include a specific open-source license. Add a license file if you want to publish it publicly on GitHub.

## Support

For local setup issues, verify:

- your `.env` file is present and correctly formatted
- your `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, and `PINECONE_API_KEY` are valid
- your Pinecone index exists and matches the embedding model dimension
- the sample KB has been indexed before testing the chat flow
