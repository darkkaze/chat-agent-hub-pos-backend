from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from models.auth import Token
from models.pos_models import SaleWebhook
from .schemas.pos_schemas import (
    WebhookRequest, WebhookResponse, WebhookListResponse,
    WebhookTestResponse, MessageResponse
)
from helpers.auth import get_auth_token, require_admin_or_agent
from helpers.webhook_notifier import test_webhook
from datetime import datetime, timezone


router = APIRouter(prefix="/webhooks", tags=["pos_webhooks"])


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Create new webhook for sale notifications."""
    await require_admin_or_agent(token, db_session)

    new_webhook = SaleWebhook(
        name=webhook_data.name,
        url=webhook_data.url,
        is_active=webhook_data.is_active if webhook_data.is_active is not None else True,
        auth_config=webhook_data.auth_config or "{}",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db_session.add(new_webhook)
    db_session.commit()
    db_session.refresh(new_webhook)

    return WebhookResponse(
        id=new_webhook.id,
        name=new_webhook.name,
        url=new_webhook.url,
        is_active=new_webhook.is_active,
        auth_config=new_webhook.auth_config,
        created_at=new_webhook.created_at,
        updated_at=new_webhook.updated_at
    )


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """List all webhooks."""
    await require_admin_or_agent(token, db_session)

    statement = select(SaleWebhook).order_by(SaleWebhook.created_at.desc())
    webhooks = db_session.exec(statement).all()

    webhook_responses = [
        WebhookResponse(
            id=webhook.id,
            name=webhook.name,
            url=webhook.url,
            is_active=webhook.is_active,
            auth_config=webhook.auth_config,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at
        )
        for webhook in webhooks
    ]

    return WebhookListResponse(webhooks=webhook_responses)


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Get webhook details."""
    await require_admin_or_agent(token, db_session)

    webhook = db_session.get(SaleWebhook, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        is_active=webhook.is_active,
        auth_config=webhook.auth_config,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    webhook_data: WebhookRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Update webhook."""
    await require_admin_or_agent(token, db_session)

    webhook = db_session.get(SaleWebhook, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    webhook.name = webhook_data.name
    webhook.url = webhook_data.url
    webhook.is_active = webhook_data.is_active if webhook_data.is_active is not None else webhook.is_active
    webhook.auth_config = webhook_data.auth_config or "{}"
    webhook.updated_at = datetime.now(timezone.utc)

    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        is_active=webhook.is_active,
        auth_config=webhook.auth_config,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at
    )


@router.delete("/{webhook_id}", response_model=MessageResponse)
async def delete_webhook(
    webhook_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Delete webhook (hard delete)."""
    await require_admin_or_agent(token, db_session)

    webhook = db_session.get(SaleWebhook, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    db_session.delete(webhook)
    db_session.commit()

    return MessageResponse(message="Webhook deleted successfully")


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook_endpoint(
    webhook_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Test webhook with dummy sale data."""
    await require_admin_or_agent(token, db_session)

    webhook = db_session.get(SaleWebhook, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    result = await test_webhook(webhook)

    return WebhookTestResponse(
        success=result["success"],
        status_code=result["status_code"],
        response_body=result["response_body"],
        error=result["error"]
    )
