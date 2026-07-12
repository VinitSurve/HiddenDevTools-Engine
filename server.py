import uvicorn
from fastapi import FastAPI
import logging

from config import PORT
from routers.health import router as health_router
from routers.meta_webhook import router as meta_webhook_router

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("Server")

def create_app() -> FastAPI:
    app = FastAPI(
        title="HiddenDevTools Webhook Server",
        description="FastAPI server for receiving Meta webhooks.",
        version="1.0.0"
    )

    app.include_router(health_router)
    app.include_router(meta_webhook_router)

    return app

app = create_app()

if __name__ == "__main__":
    logger.info(f"Starting server on port {PORT}...")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=True)
