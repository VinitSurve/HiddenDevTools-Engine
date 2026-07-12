from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for monitoring and deployments.
    """
    return {
        "status": "ok",
        "service": "HiddenDevTools Webhook",
        "version": "1.0"
    }
