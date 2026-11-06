from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.core.config import get_settings, BASE_DIR
from app.core.logging import configure_logging
from app.services.audit import init_db


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

configure_logging()

settings = get_settings()


# --------------------------------------------------
# APPLICATION LIFESPAN
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Startup
    init_db()

    yield

    # Shutdown
    pass


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Enterprise IT Support RAG Assistant",
    lifespan=lifespan,
)


# --------------------------------------------------
# ROUTERS
# --------------------------------------------------

app.include_router(router)


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

STATIC_DIR = BASE_DIR / "static"

STATIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# --------------------------------------------------
# JINJA2 TEMPLATES
# --------------------------------------------------

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name
        }
    )
