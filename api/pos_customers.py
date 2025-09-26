from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from database import get_session
from models.auth import Token
from models.pos_models import Customer, Sale
from .schemas.pos_schemas import (
    CustomerRequest, CustomerResponse, CustomerWalletRequest,
    CustomerSearchResponse, SaleResponse, MessageResponse
)
from helpers.auth import get_auth_token, require_admin_or_agent
from datetime import datetime, timezone
from decimal import Decimal

router = APIRouter(prefix="/customers", tags=["pos_customers"])


@router.get("/search", response_model=CustomerSearchResponse)
async def search_customers(
    phone: str = Query(..., description="Phone number to search (partial match)"),
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Search customers by phone number using LIKE pattern."""
    await require_admin_or_agent(token, db_session)

    # Search using LIKE pattern
    statement = select(Customer).where(
        Customer.phone.like(f'%{phone}%'),
        Customer.is_active == True
    )
    customers = db_session.exec(statement).all()

    customer_responses = [
        CustomerResponse(
            id=customer.id,
            phone=customer.phone,
            name=customer.name,
            loyalty_points=customer.loyalty_points,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at
        )
        for customer in customers
    ]

    return CustomerSearchResponse(customers=customer_responses)


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Create new customer or return existing one if phone already exists."""
    await require_admin_or_agent(token, db_session)

    # Check if customer already exists
    existing_customer = db_session.exec(
        select(Customer).where(Customer.phone == customer_data.phone)
    ).first()

    if existing_customer:
        return CustomerResponse(
            id=existing_customer.id,
            phone=existing_customer.phone,
            name=existing_customer.name,
            loyalty_points=existing_customer.loyalty_points,
            is_active=existing_customer.is_active,
            created_at=existing_customer.created_at,
            updated_at=existing_customer.updated_at
        )

    # Create new customer
    new_customer = Customer(
        phone=customer_data.phone,
        name=customer_data.name,
        loyalty_points=Decimal("0.00"),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db_session.add(new_customer)
    db_session.commit()
    db_session.refresh(new_customer)

    return CustomerResponse(
        id=new_customer.id,
        phone=new_customer.phone,
        name=new_customer.name,
        loyalty_points=new_customer.loyalty_points,
        is_active=new_customer.is_active,
        created_at=new_customer.created_at,
        updated_at=new_customer.updated_at
    )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Update customer information (name only)."""
    await require_admin_or_agent(token, db_session)

    customer = db_session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Update only name, phone cannot be changed
    customer.name = customer_data.name
    customer.updated_at = datetime.now(timezone.utc)

    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    return CustomerResponse(
        id=customer.id,
        phone=customer.phone,
        name=customer.name,
        loyalty_points=customer.loyalty_points,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at
    )


@router.put("/{customer_id}/wallet", response_model=CustomerResponse)
async def update_customer_wallet(
    customer_id: str,
    wallet_data: CustomerWalletRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Update customer loyalty points."""
    await require_admin_or_agent(token, db_session)

    customer = db_session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    customer.loyalty_points = wallet_data.loyalty_points
    customer.updated_at = datetime.now(timezone.utc)

    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    return CustomerResponse(
        id=customer.id,
        phone=customer.phone,
        name=customer.name,
        loyalty_points=customer.loyalty_points,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at
    )


@router.get("/{customer_id}/sales", response_model=list[SaleResponse])
async def get_customer_sales(
    customer_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Get sales history for a customer."""
    await require_admin_or_agent(token, db_session)

    customer = db_session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    statement = select(Sale).where(Sale.customer_id == customer_id).order_by(Sale.created_at.desc())
    sales = db_session.exec(statement).all()

    sale_responses = []
    for sale in sales:
        sale_responses.append(SaleResponse(
            id=sale.id,
            customer_id=sale.customer_id,
            customer=CustomerResponse(
                id=customer.id,
                phone=customer.phone,
                name=customer.name,
                loyalty_points=customer.loyalty_points,
                is_active=customer.is_active,
                created_at=customer.created_at,
                updated_at=customer.updated_at
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

    return sale_responses