"""
Feature: Customer management for POS system
  As a POS operator
  I want to manage customers
  So that I can track customer information and loyalty points

Scenario: Search customer by phone number
  Given an admin user is authenticated
  When they search for a customer by phone
  Then the system returns matching customers

Scenario: Create new customer
  Given an admin user is authenticated
  When they create a customer with valid data
  Then the system creates the customer successfully
  And returns customer data with generated ID

Scenario: Create customer with existing phone
  Given an admin user is authenticated
  And a customer already exists with the same phone
  When they create a customer with that phone
  Then the system returns the existing customer

Scenario: Update customer information
  Given an admin user is authenticated
  And a customer exists
  When they update the customer name
  Then the system updates the customer successfully

Scenario: Update customer loyalty points
  Given an admin user is authenticated
  And a customer exists
  When they update the customer's loyalty points
  Then the system updates the wallet successfully

Scenario: Get customer sales history
  Given an admin user is authenticated
  And a customer has sales
  When they request the customer's sales history
  Then the system returns the sales list
"""

import pytest
from sqlmodel import create_engine, Session, SQLModel
from models.auth import User, Token, TokenUser, UserRole
from models.pos_models import Customer, Sale
from database import get_session
from api.pos_customers import (
    search_customers, create_customer, update_customer,
    update_customer_wallet, get_customer_sales
)
from api.schemas.pos_schemas import CustomerRequest, CustomerWalletRequest
from datetime import datetime, timedelta, timezone
from decimal import Decimal


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="admin_token")
def admin_token_fixture(session):
    """Create admin user and token for testing."""
    admin_user = User(
        username="admin",
        hashed_password="hashed_secret",
        role=UserRole.ADMIN
    )

    token = Token(
        access_token="admin_token",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_revoked=False
    )

    session.add_all([admin_user, token])
    session.commit()
    session.refresh(admin_user)
    session.refresh(token)

    token_user = TokenUser(token_id=token.id, user_id=admin_user.id)
    session.add(token_user)
    session.commit()

    return token


@pytest.mark.asyncio
async def test_search_customers_by_phone(session, admin_token):
    """Test searching customers by phone number."""
    # Given customers exist
    customer1 = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("50.00")
    )
    customer2 = Customer(
        phone="+1987654321",
        name="Jane Smith",
        loyalty_points=Decimal("25.00")
    )
    session.add_all([customer1, customer2])
    session.commit()

    # When searching by partial phone
    result = await search_customers(
        phone="1234",
        token=admin_token,
        db_session=session
    )

    # Then return matching customer
    assert len(result.customers) == 1
    assert result.customers[0].phone == "+1234567890"
    assert result.customers[0].name == "John Doe"


@pytest.mark.asyncio
async def test_create_new_customer(session, admin_token):
    """Test creating a new customer."""
    # When creating a new customer
    customer_data = CustomerRequest(
        phone="+1234567890",
        name="John Doe"
    )

    result = await create_customer(
        customer_data=customer_data,
        token=admin_token,
        db_session=session
    )

    # Then customer is created successfully
    assert result.phone == "+1234567890"
    assert result.name == "John Doe"
    assert result.loyalty_points == Decimal("0.00")
    assert result.is_active == True
    assert result.id.startswith("customer_")


@pytest.mark.asyncio
async def test_create_customer_existing_phone(session, admin_token):
    """Test creating customer with existing phone returns existing customer."""
    # Given customer already exists
    existing_customer = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("100.00")
    )
    session.add(existing_customer)
    session.commit()
    session.refresh(existing_customer)

    # When creating customer with same phone
    customer_data = CustomerRequest(
        phone="+1234567890",
        name="Different Name"
    )

    result = await create_customer(
        customer_data=customer_data,
        token=admin_token,
        db_session=session
    )

    # Then return existing customer
    assert result.id == existing_customer.id
    assert result.phone == "+1234567890"
    assert result.name == "John Doe"  # Original name preserved
    assert result.loyalty_points == Decimal("100.00")


@pytest.mark.asyncio
async def test_update_customer_name(session, admin_token):
    """Test updating customer name."""
    # Given customer exists
    customer = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("50.00")
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    # When updating customer name
    customer_data = CustomerRequest(
        phone="+1234567890",  # Phone cannot be changed
        name="John Smith"
    )

    result = await update_customer(
        customer_id=customer.id,
        customer_data=customer_data,
        token=admin_token,
        db_session=session
    )

    # Then customer name is updated
    assert result.id == customer.id
    assert result.name == "John Smith"
    assert result.phone == "+1234567890"  # Phone unchanged


@pytest.mark.asyncio
async def test_update_customer_wallet(session, admin_token):
    """Test updating customer loyalty points."""
    # Given customer exists
    customer = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("50.00")
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    # When updating loyalty points
    wallet_data = CustomerWalletRequest(
        loyalty_points=Decimal("150.75")
    )

    result = await update_customer_wallet(
        customer_id=customer.id,
        wallet_data=wallet_data,
        token=admin_token,
        db_session=session
    )

    # Then loyalty points are updated
    assert result.id == customer.id
    assert result.loyalty_points == Decimal("150.75")


@pytest.mark.asyncio
async def test_get_customer_sales_history(session, admin_token):
    """Test getting customer sales history."""
    # Given customer and sales exist
    customer = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("50.00")
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    sale1 = Sale(
        customer_id=customer.id,
        items='[{"type": "product", "name": "Test Product", "description": "Test", "unit_price": 10.00, "quantity": 2, "total": 20.00}]',
        subtotal=Decimal("20.00"),
        total_amount=Decimal("20.00"),
        payment_methods='[{"method": "cash", "amount": 20.00}]'
    )
    sale2 = Sale(
        customer_id=customer.id,
        items='[{"type": "product", "name": "Another Product", "description": "Test 2", "unit_price": 15.00, "quantity": 1, "total": 15.00}]',
        subtotal=Decimal("15.00"),
        total_amount=Decimal("15.00"),
        payment_methods='[{"method": "card", "amount": 15.00}]'
    )
    session.add_all([sale1, sale2])
    session.commit()

    # When getting sales history
    result = await get_customer_sales(
        customer_id=customer.id,
        token=admin_token,
        db_session=session
    )

    # Then return sales list
    assert len(result) == 2
    assert result[0].customer_id == customer.id
    assert result[0].customer.name == "John Doe"
    assert len(result[0].items) == 1
    assert result[0].items[0]["name"] == "Test Product"


@pytest.mark.asyncio
async def test_customer_not_found_error(session, admin_token):
    """Test error when customer is not found."""
    # When updating non-existent customer
    customer_data = CustomerRequest(
        phone="+1234567890",
        name="John Doe"
    )

    # Then raise 404 error
    with pytest.raises(Exception) as exc_info:
        await update_customer(
            customer_id="nonexistent_id",
            customer_data=customer_data,
            token=admin_token,
            db_session=session
        )
    assert "404" in str(exc_info.value)