"""
POS Sales Reports API

Provides sales reporting endpoints with filtering by date range and staff member.
Reports include timezone-aware timestamp conversion and CSV-compatible data format.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal

from database import get_session
from models.auth import Token
from models.pos_models import Sale, Customer, Staff
from .schemas.pos_schemas import SalesReportResponse, SaleResponse, CustomerResponse, StaffResponse
from helpers.auth import get_auth_token, require_admin_or_agent
from models.helper import convert_utc_to_local

router = APIRouter(prefix="/reports", tags=["pos_reports"])


def build_sale_response(sale: Sale, customer: Customer, staff: Staff) -> SaleResponse:
    """
    Build SaleResponse with timezone-converted timestamps.
    Converts UTC timestamps to local timezone for API response.
    """
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
            created_at=convert_utc_to_local(customer.created_at),
            updated_at=convert_utc_to_local(customer.updated_at)
        ),
        staff=StaffResponse(
            id=staff.id,
            name=staff.name,
            schedule=staff.schedule,
            is_active=staff.is_active,
            created_at=convert_utc_to_local(staff.created_at),
            updated_at=convert_utc_to_local(staff.updated_at)
        ),
        items=sale.get_items(),
        subtotal=sale.subtotal,
        discount_amount=sale.discount_amount,
        total_amount=sale.total_amount,
        loyalty_points_generated=sale.loyalty_points_generated,
        payment_methods=sale.get_payment_methods(),
        tip_amount=sale.tip_amount,
        delivered_at=convert_utc_to_local(sale.delivered_at),
        created_at=convert_utc_to_local(sale.created_at),
        updated_at=convert_utc_to_local(sale.updated_at)
    )


@router.get("/sales/", response_model=SalesReportResponse)
async def get_sales_report(
    start_date: str = Query(..., description="Start date in ISO format (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date in ISO format (YYYY-MM-DD)"),
    staff_id: str = Query("all", description="Staff ID or 'all' for all staff"),
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Get sales report filtered by date range and staff member with CSV-compatible data."""
    await require_admin_or_agent(token, db_session)

    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Validate date range
    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date"
        )

    # Get timezone from environment
    tz_name = os.getenv('TZ', 'UTC')
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('UTC')

    # Convert dates to local timezone with specific times
    # Start: 00:00:00 local time
    start_datetime_local = start_dt.replace(hour=0, minute=0, second=0, tzinfo=tz)
    start_datetime_utc = start_datetime_local.astimezone(timezone.utc)

    # End: 23:59:59 local time
    end_datetime_local = end_dt.replace(hour=23, minute=59, second=59, tzinfo=tz)
    end_datetime_utc = end_datetime_local.astimezone(timezone.utc)

    # Build query
    statement = (
        select(Sale, Customer, Staff)
        .join(Customer, Sale.customer_id == Customer.id)
        .join(Staff, Sale.staff_id == Staff.id)
        .where(
            Sale.created_at >= start_datetime_utc,
            Sale.created_at <= end_datetime_utc
        )
    )

    # Filter by staff if specified
    if staff_id and staff_id != "all":
        statement = statement.where(Sale.staff_id == staff_id)

    # Order by date descending
    statement = statement.order_by(Sale.created_at.desc())

    results = db_session.exec(statement).all()

    # Build responses and calculate total
    sale_responses = []
    total_amount = Decimal('0')

    for sale, customer, staff in results:
        response = build_sale_response(sale, customer, staff)
        sale_responses.append(response)
        total_amount += sale.total_amount

    return SalesReportResponse(
        sales=sale_responses,
        total_amount=total_amount,
        total_sales=len(sale_responses),
        filters={
            "start_date": start_date,
            "end_date": end_date,
            "staff_id": staff_id if staff_id != "all" else None
        }
    )
