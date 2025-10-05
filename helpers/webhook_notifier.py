"""
Webhook Notifier Helper

Handles webhook notifications for sale events.
Sends sale data to all active webhooks using fire-and-forget approach.
"""

import httpx
import json
from sqlmodel import Session, select
from models.pos_models import SaleWebhook, Sale, Customer, Staff
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_sale_webhook_payload(sale: Sale, customer: Customer, staff: Staff) -> dict:
    """
    Generate webhook payload from sale data.

    Returns JSON-serializable dict with complete sale information.
    """
    return {
        "sale_id": sale.id,
        "customer": {
            "id": customer.id,
            "phone": customer.phone,
            "name": customer.name,
            "loyalty_points": str(customer.loyalty_points),
        },
        "staff": {
            "id": staff.id,
            "name": staff.name,
        },
        "items": sale.get_items(),
        "subtotal": str(sale.subtotal),
        "discount_amount": str(sale.discount_amount),
        "total_amount": str(sale.total_amount),
        "loyalty_points_generated": sale.loyalty_points_generated,
        "payment_methods": sale.get_payment_methods(),
        "created_at": sale.created_at.isoformat(),
    }


def apply_webhook_auth(headers: dict, auth_config: dict) -> dict:
    """
    Apply authentication config to request headers.

    Supports:
    - bearer: {"type": "bearer", "token": "xxx"}
    - apikey: {"type": "apikey", "header": "X-API-Key", "token": "xxx"}
    - basic: {"type": "basic", "username": "xxx", "password": "xxx"}
    """
    if not auth_config or not auth_config.get("type"):
        return headers

    auth_type = auth_config.get("type", "").lower()

    if auth_type == "bearer":
        token = auth_config.get("token", "")
        headers["Authorization"] = f"Bearer {token}"

    elif auth_type == "apikey":
        header_name = auth_config.get("header", "X-API-Key")
        token = auth_config.get("token", "")
        headers[header_name] = token

    elif auth_type == "basic":
        username = auth_config.get("username", "")
        password = auth_config.get("password", "")
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    return headers


async def notify_single_webhook(webhook: SaleWebhook, payload: dict):
    """
    Notify a single webhook with sale data.

    Fire-and-forget: errors are logged but don't raise exceptions.
    """
    try:
        headers = {"Content-Type": "application/json"}
        auth_config = webhook.get_auth_config()
        headers = apply_webhook_auth(headers, auth_config)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers
            )

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook {webhook.name} ({webhook.id}) notified successfully: {response.status_code}")
            else:
                logger.warning(f"Webhook {webhook.name} ({webhook.id}) returned status {response.status_code}: {response.text[:200]}")

    except httpx.TimeoutException:
        logger.error(f"Webhook {webhook.name} ({webhook.id}) timed out")
    except httpx.RequestError as e:
        logger.error(f"Webhook {webhook.name} ({webhook.id}) request error: {str(e)}")
    except Exception as e:
        logger.error(f"Webhook {webhook.name} ({webhook.id}) unexpected error: {str(e)}")


async def notify_sale_to_webhooks(sale: Sale, customer: Customer, staff: Staff, db_session: Session):
    """
    Notify all active webhooks about a new sale.

    This function is called via BackgroundTasks after sale creation.
    Each webhook is notified independently - failures don't affect others.
    """
    # Get all active webhooks
    statement = select(SaleWebhook).where(SaleWebhook.is_active == True)
    webhooks = db_session.exec(statement).all()

    if not webhooks:
        logger.info("No active webhooks to notify")
        return

    # Generate payload once
    payload = generate_sale_webhook_payload(sale, customer, staff)

    # Notify each webhook independently
    for webhook in webhooks:
        await notify_single_webhook(webhook, payload)


async def test_webhook(webhook: SaleWebhook) -> dict:
    """
    Test a webhook with dummy sale data.

    Returns dict with success status, status_code, response_body, and error.
    """
    # Generate dummy payload
    dummy_payload = {
        "sale_id": "sale_test123456",
        "customer": {
            "id": "customer_test123",
            "phone": "5551234567",
            "name": "Test Customer",
            "loyalty_points": "100.00",
        },
        "staff": {
            "id": "staff_test123",
            "name": "Test Staff",
        },
        "items": [
            {
                "type": "product",
                "product_id": "product_test123",
                "name": "Test Product",
                "description": "Test product description",
                "unit_price": "50.00",
                "quantity": 2,
                "total": "100.00"
            }
        ],
        "subtotal": "100.00",
        "discount_amount": "10.00",
        "total_amount": "90.00",
        "loyalty_points_generated": 9,
        "payment_methods": [
            {
                "method": "cash",
                "amount": "90.00",
                "reference": None
            }
        ],
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        headers = {"Content-Type": "application/json"}
        auth_config = webhook.get_auth_config()
        headers = apply_webhook_auth(headers, auth_config)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=dummy_payload,
                headers=headers
            )

            return {
                "success": response.status_code >= 200 and response.status_code < 300,
                "status_code": response.status_code,
                "response_body": response.text[:500],  # Limit response size
                "error": None
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error": "Request timed out (10 seconds)"
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error": f"Request error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error": f"Unexpected error: {str(e)}"
        }
