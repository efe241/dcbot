from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.api import auth, cpx, users, rewards, admin
from backend.config import settings
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("backend.main")

app = FastAPI(
    title="Discord Coin + CPX Research Reward System",
    description="Backend service managing virtual Discord Coins, CPX postbacks, user balances, security, and fraud prevention.",
    version="1.0.0"
)

# Enable CORS for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(cpx.router)
app.include_router(users.router)
app.include_router(rewards.router)
app.include_router(admin.router)

# Mount frontend static files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    css_path = os.path.join(frontend_path, "css")
    js_path = os.path.join(frontend_path, "js")
    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")

@app.on_event("startup")
async def on_startup():
    logger.info("Initializing database schema...")
    await init_db()
    logger.info("Startup complete.")

@app.get("/")
async def read_root():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Discord Coin + CPX Reward System API active"}

@app.get("/tasks")
async def read_tasks_page():
    tasks_file = os.path.join(frontend_path, "tasks.html")
    if os.path.exists(tasks_file):
        return FileResponse(tasks_file)
    return {"message": "Tasks page"}

@app.get("/admin-panel")
async def read_admin_page():
    admin_file = os.path.join(frontend_path, "admin.html")
    if os.path.exists(admin_file):
        return FileResponse(admin_file)
    return {"message": "Admin Panel"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)}
    )
