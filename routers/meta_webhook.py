from fastapi import APIRouter, Request, Query, HTTPException, BackgroundTasks, Header
from typing import Dict, Any, Optional
import uuid
import json

from services.meta_webhook_service import MetaWebhookService

router = APIRouter()
webhook_service = MetaWebhookService()

@router.get("/webhooks/meta")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """
    Endpoint for Meta to verify the webhook subscription.
    """
    if not hub_mode or not hub_verify_token or not hub_challenge:
        raise HTTPException(status_code=400, detail="Missing required query parameters")

    try:
        challenge = webhook_service.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
        return int(challenge)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/webhooks/meta")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Endpoint to receive incoming webhook events from Meta.
    Returns 200 OK immediately and processes the event in the background.
    """
    correlation_id = f"REQ_{uuid.uuid4().hex[:12]}"
    
    # 1. Read raw bytes for signature validation
    payload_bytes = await request.body()
    
    # 2. Validate Signature (Mandatory)
    is_valid = webhook_service.validate_signature(payload_bytes, x_hub_signature_256)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 3. Parse JSON
    try:
        payload_dict = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 4. Queue processing in background
    # Pass background_tasks so the dispatcher can queue worker execution
    background_tasks.add_task(webhook_service.receive_event, payload_dict, correlation_id, background_tasks)

    # 5. Return 200 immediately
    return {"status": "ok"}
