from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes import router

app = FastAPI(title="LLM Wiki API & Web UI", version="0.1.0")

# Mount attachments directory for media (images, videos, audio)
attachments_dir = Path("attachments")
attachments_dir.mkdir(parents=True, exist_ok=True)
app.mount("/attachments", StaticFiles(directory=str(attachments_dir)), name="attachments")

app.include_router(router)

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    template_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))

