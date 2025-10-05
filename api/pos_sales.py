from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from database import get_session
from models.auth import Token
from models.pos_models import Sale, Customer, Staff
from .schemas.pos_schemas import (
    SaleRequest, SaleResponse, SaleListResponse, CustomerResponse, StaffResponse
)
from helpers.auth import get_auth_token, require_admin_or_agent
from helpers.signal_notifier import notify_sale_to_signals
from datetime import datetime, timezone
from decimal import Decimal
import json


def serialize_for_json(obj):
    """
    Recursively convert Pydantic models with Decimal fields to JSON-serializable dicts.
    Handles nested structures and converts Decimal to string.
    """
    if isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return str(obj)
    elif hasattr(obj, 'dict'):
        # Pydantic model - recursively process
        data = obj.dict()
        return serialize_for_json(data)
    else:
        return obj


router = APIRouter(prefix="/sales", tags=["pos_sales"])


@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_data: SaleRequest,
    background_tasks: BackgroundTasks,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Create new sale with transaction to update customer loyalty points."""
    await require_admin_or_agent(token, db_session)

    # Validate customer exists
    customer = db_session.get(Customer, sale_data.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Validate staff exists and is active
    staff = db_session.get(Staff, sale_data.staff_id)
    if not staff or not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found or inactive"
        )

    # Validate payment methods sum equals total amount
    total_payments = sum(pm.amount for pm in sale_data.payment_methods)
    if abs(total_payments - sale_data.total_amount) > Decimal('0.01'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment methods sum must equal total amount"
        )

    try:
        # TODO: Generate embedding for sale analysis (requires vector search implementation)
        # items_text = " ".join([f"{item.name} {item.description}" for item in sale_data.items])
        # embedding_vector = await generate_embedding(items_text)

        # Create sale
        new_sale = Sale(
            customer_id=sale_data.customer_id,
            staff_id=sale_data.staff_id,
            subtotal=sale_data.subtotal,
            discount_amount=sale_data.discount_amount,
            total_amount=sale_data.total_amount,
            loyalty_points_generated=sale_data.loyalty_points_generated,
            embedding_vector=None,  # Vector search not implemented yet
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # Set JSON fields using helper methods (serialize Decimals to strings)
        new_sale.set_items(serialize_for_json(sale_data.items))
        new_sale.set_payment_methods(serialize_for_json(sale_data.payment_methods))

        db_session.add(new_sale)
        db_session.flush()  # Get sale ID

        # Update customer loyalty points
        customer.loyalty_points += Decimal(str(sale_data.loyalty_points_generated))
        customer.updated_at = datetime.now(timezone.utc)
        db_session.add(customer)

        # Commit transaction
        db_session.commit()
        db_session.refresh(new_sale)
        db_session.refresh(customer)

        # Fire-and-forget webhook notifications
        background_tasks.add_task(notify_sale_to_signals, new_sale, customer, staff, db_session)

        return SaleResponse(
            id=new_sale.id,
            customer_id=new_sale.customer_id,
            staff_id=new_sale.staff_id,
            customer=CustomerResponse(
                id=customer.id,
                phone=customer.phone,
                name=customer.name,
                loyalty_points=customer.loyalty_points,
                is_active=customer.is_active,
                created_at=customer.created_at,
                updated_at=customer.updated_at
            ),
            staff=StaffResponse(
                id=staff.id,
                name=staff.name,
                schedule=staff.schedule,
                is_active=staff.is_active,
                created_at=staff.created_at,
                updated_at=staff.updated_at
            ),
            items=new_sale.get_items(),
            subtotal=new_sale.subtotal,
            discount_amount=new_sale.discount_amount,
            total_amount=new_sale.total_amount,
            loyalty_points_generated=new_sale.loyalty_points_generated,
            payment_methods=new_sale.get_payment_methods(),
            created_at=new_sale.created_at,
            updated_at=new_sale.updated_at
        )

    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sale: {str(e)}"
        )


@router.get("/", response_model=SaleListResponse)
async def list_sales(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """List sales with pagination and customer information."""
    await require_admin_or_agent(token, db_session)

    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    total_statement = select(Sale)
    total_count = len(db_session.exec(total_statement).all())

    # Get paginated sales with customer and staff information
    statement = (
        select(Sale, Customer, Staff)
        .join(Customer, Sale.customer_id == Customer.id)
        .join(Staff, Sale.staff_id == Staff.id)
        .order_by(Sale.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    results = db_session.exec(statement).all()

    sale_responses = []
    for sale, customer, staff in results:
        sale_responses.append(SaleResponse(
            id=sale.id,
            customer_id=sale.customer_id,
            staff_id=sale.staff_id,
            customer=CustomerResponse(
                id=customer.id,
                phone=customer.phone,
                name=customer.name,
                loyalty_points=customer.loyalty_points,
                is_active=customer.is_active,
                created_at=customer.created_at,
                updated_at=customer.updated_at
            ),
            staff=StaffResponse(
                id=staff.id,
                name=staff.name,
                schedule=staff.schedule,
                is_active=staff.is_active,
                created_at=staff.created_at,
                updated_at=staff.updated_at
            ),
            items=sale.get_items(),
            subtotal=sale.subtotal,
            discount_amount=sale.discount_amount,
            total_amount=sale.total_amount,
            loyalty_points_generated=sale.loyalty_points_generated,
            payment_methods=sale.get_payment_methods(),
            created_at=sale.created_at,
            updated_at=sale.updated_at
        ))

    return SaleListResponse(
        sales=sale_responses,
        total=total_count,
        page=page,
        page_size=page_size
    )


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Get detailed information for a specific sale."""
    await require_admin_or_agent(token, db_session)

    sale = db_session.get(Sale, sale_id)
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )

    customer = db_session.get(Customer, sale.customer_id)
    staff = db_session.get(Staff, sale.staff_id)

    return SaleResponse(
        id=sale.id,
        customer_id=sale.customer_id,
        staff_id=sale.staff_id,
        customer=CustomerResponse(
            id=customer.id,
            phone=customer.phone,
            name=customer.name,
            loyalty_points=customer.loyalty_points,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at
        ) if customer else None,
        staff=StaffResponse(
            id=staff.id,
            name=staff.name,
            schedule=staff.schedule,
            is_active=staff.is_active,
            created_at=staff.created_at,
            updated_at=staff.updated_at
        ) if staff else None,
        items=sale.get_items(),
        subtotal=sale.subtotal,
        discount_amount=sale.discount_amount,
        total_amount=sale.total_amount,
        loyalty_points_generated=sale.loyalty_points_generated,
        payment_methods=sale.get_payment_methods(),
        created_at=sale.created_at,
        updated_at=sale.updated_at
    )