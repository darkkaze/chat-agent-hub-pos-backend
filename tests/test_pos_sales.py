"""
Feature: Sales management for POS system
  As a POS operator
  I want to create and manage sales
  So that I can process customer transactions

Scenario: Create sale with valid data
  Given an admin user is authenticated
  And a customer exists
  When they create a sale with valid items and payments
  Then the system creates the sale successfully
  And updates customer loyalty points
  And generates embedding vector

Scenario: Create sale with invalid payment total
  Given an admin user is authenticated
  And a customer exists
  When they create a sale where payment methods don't sum to total
  Then the system returns validation error

Scenario: Create sale for non-existent customer
  Given an admin user is authenticated
  When they create a sale for non-existent customer
  Then the system returns customer not found error

Scenario: List sales with pagination
  Given an admin user is authenticated
  And multiple sales exist
  When they request sales list with pagination
  Then the system returns paginated sales with customer info

Scenario: Get specific sale details
  Given an admin user is authenticated
  And a sale exists
  When they request sale details
  Then the system returns complete sale information
"""

import pytest
from sqlmodel import create_engine, Session, SQLModel
from models.auth import User, Token, TokenUser, UserRole
from models.pos_models import Customer, Sale, PaymentMethod
from database import get_session
from api.pos_sales import create_sale, list_sales, get_sale
from api.schemas.pos_schemas import (
    SaleRequest, SaleItem, PaymentMethodItem
)
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch, AsyncMock


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


@pytest.fixture(name="test_customer")
def test_customer_fixture(session):
    """Create test customer."""
    customer = Customer(
        phone="+1234567890",
        name="John Doe",
        loyalty_points=Decimal("50.00")
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


@pytest.mark.asyncio
@patch('api.pos_sales.generate_embedding')
async def test_create_sale_success(mock_embedding, session, admin_token, test_customer):
    """Test creating a sale successfully."""
    # Given embedding generation returns a vector
    mock_embedding.return_value = [0.1, 0.2, 0.3]

    # When creating a sale
    sale_items = [
        SaleItem(
            type="product",
            product_id="prod_123",
            name="Test Product",
            description="Test product description",
            unit_price=Decimal("10.00"),
            quantity=2,
            total=Decimal("20.00")
        ),
        SaleItem(
            type="discount",
            name="Customer Discount",
            description="Loyal customer discount",
            unit_price=Decimal("-2.00"),
            quantity=1,
            total=Decimal("-2.00"),
            discount_type="fixed",
            discount_value=Decimal("2.00"),
            applied_to_amount=Decimal("20.00")
        )
    ]

    payment_methods = [
        PaymentMethodItem(
            method=PaymentMethod.CASH,
            amount=Decimal("18.00")
        )
    ]

    sale_data = SaleRequest(
        customer_id=test_customer.id,
        items=sale_items,
        subtotal=Decimal("20.00"),
        discount_amount=Decimal("2.00"),
        total_amount=Decimal("18.00"),
        loyalty_points_generated=18,  # 1 point per dollar
        payment_methods=payment_methods
    )

    result = await create_sale(
        sale_data=sale_data,
        token=admin_token,
        db_session=session
    )

    # Then sale is created successfully
    assert result.customer_id == test_customer.id
    assert result.total_amount == Decimal("18.00")
    assert result.loyalty_points_generated == 18
    assert len(result.items) == 2
    assert result.items[0]["name"] == "Test Product"
    assert result.customer.name == "John Doe"
    assert result.id.startswith("sale_")

    # And customer loyalty points were updated
    updated_customer = session.get(Customer, test_customer.id)
    assert updated_customer.loyalty_points == Decimal("68.00")  # 50.00 + 18

    # And embedding generation was called
    mock_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_create_sale_invalid_payment_total(session, admin_token, test_customer):
    """Test creating sale with invalid payment total."""
    # When creating sale with mismatched payment total
    sale_items = [
        SaleItem(
            type="product",
            name="Test Product",
            description="Test product description",
            unit_price=Decimal("10.00"),
            quantity=2,
            total=Decimal("20.00")
        )
    ]

    payment_methods = [
        PaymentMethodItem(
            method=PaymentMethod.CASH,
            amount=Decimal("15.00")  # Doesn't match total_amount
        )
    ]

    sale_data = SaleRequest(
        customer_id=test_customer.id,
        items=sale_items,
        subtotal=Decimal("20.00"),
        total_amount=Decimal("20.00"),
        payment_methods=payment_methods
    )

    # Then validation error is raised
    with pytest.raises(Exception) as exc_info:
        await create_sale(
            sale_data=sale_data,
            token=admin_token,
            db_session=session
        )
    assert "400" in str(exc_info.value) or "payment methods sum" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_create_sale_customer_not_found(session, admin_token):
    """Test creating sale for non-existent customer."""
    # When creating sale for non-existent customer
    sale_items = [
        SaleItem(
            type="product",
            name="Test Product",
            description="Test product description",
            unit_price=Decimal("10.00"),
            quantity=1,
            total=Decimal("10.00")
        )
    ]

    payment_methods = [
        PaymentMethodItem(
            method=PaymentMethod.CASH,
            amount=Decimal("10.00")
        )
    ]

    sale_data = SaleRequest(
        customer_id="nonexistent_customer",
        items=sale_items,
        subtotal=Decimal("10.00"),
        total_amount=Decimal("10.00"),
        payment_methods=payment_methods
    )

    # Then customer not found error is raised
    with pytest.raises(Exception) as exc_info:
        await create_sale(
            sale_data=sale_data,
            token=admin_token,
            db_session=session
        )
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_list_sales_with_pagination(session, admin_token, test_customer):
    """Test listing sales with pagination."""
    # Given multiple sales exist
    sale1 = Sale(
        customer_id=test_customer.id,
        items='[{"type": "product", "name": "Product 1", "description": "Desc 1", "unit_price": 10.00, "quantity": 1, "total": 10.00}]',
        subtotal=Decimal("10.00"),
        total_amount=Decimal("10.00"),
        payment_methods='[{"method": "cash", "amount": 10.00}]'
    )
    sale2 = Sale(
        customer_id=test_customer.id,
        items='[{"type": "product", "name": "Product 2", "description": "Desc 2", "unit_price": 15.00, "quantity": 1, "total": 15.00}]',
        subtotal=Decimal("15.00"),
        total_amount=Decimal("15.00"),
        payment_methods='[{"method": "card", "amount": 15.00}]'
    )
    session.add_all([sale1, sale2])
    session.commit()

    # When listing sales with pagination
    result = await list_sales(
        page=1,
        page_size=10,
        token=admin_token,
        db_session=session
    )

    # Then return paginated sales with customer info
    assert len(result.sales) == 2
    assert result.total == 2
    assert result.page == 1
    assert result.page_size == 10
    assert result.sales[0].customer.name == "John Doe"
    assert result.sales[1].customer.name == "John Doe"


@pytest.mark.asyncio
async def test_list_sales_pagination_limits(session, admin_token, test_customer):
    """Test sales list pagination with page limits."""
    # Given 3 sales exist
    for i in range(3):
        sale = Sale(
            customer_id=test_customer.id,
            items=f'[{{"type": "product", "name": "Product {i+1}", "description": "Desc", "unit_price": 10.00, "quantity": 1, "total": 10.00}}]',
            subtotal=Decimal("10.00"),
            total_amount=Decimal("10.00"),
            payment_methods='[{"method": "cash", "amount": 10.00}]'
        )
        session.add(sale)
    session.commit()

    # When requesting page 1 with page_size 2
    result = await list_sales(
        page=1,
        page_size=2,
        token=admin_token,
        db_session=session
    )

    # Then return only 2 sales
    assert len(result.sales) == 2
    assert result.total == 3
    assert result.page == 1
    assert result.page_size == 2


@pytest.mark.asyncio
async def test_get_sale_details(session, admin_token, test_customer):
    """Test getting specific sale details."""
    # Given a sale exists
    sale = Sale(
        customer_id=test_customer.id,
        items='[{"type": "product", "name": "Detailed Product", "description": "Detailed description", "unit_price": 25.50, "quantity": 2, "total": 51.00}]',
        subtotal=Decimal("51.00"),
        total_amount=Decimal("51.00"),
        loyalty_points_generated=51,
        payment_methods='[{"method": "card", "amount": 51.00, "reference": "CARD123"}]'
    )
    session.add(sale)
    session.commit()
    session.refresh(sale)

    # When getting sale details
    result = await get_sale(
        sale_id=sale.id,
        token=admin_token,
        db_session=session
    )

    # Then return complete sale information
    assert result.id == sale.id
    assert result.customer_id == test_customer.id
    assert result.customer.name == "John Doe"
    assert result.total_amount == Decimal("51.00")
    assert result.loyalty_points_generated == 51
    assert len(result.items) == 1
    assert result.items[0]["name"] == "Detailed Product"
    assert len(result.payment_methods) == 1
    assert result.payment_methods[0]["method"] == "card"
    assert result.payment_methods[0]["reference"] == "CARD123"


@pytest.mark.asyncio
async def test_get_sale_not_found(session, admin_token):
    """Test getting non-existent sale."""
    # When getting non-existent sale
    with pytest.raises(Exception) as exc_info:
        await get_sale(
            sale_id="nonexistent_sale",
            token=admin_token,
            db_session=session
        )

    # Then raise 404 error
    assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
@patch('api.pos_sales.generate_embedding')
async def test_create_sale_multiple_payment_methods(mock_embedding, session, admin_token, test_customer):
    """Test creating sale with multiple payment methods."""
    # Given embedding generation returns a vector
    mock_embedding.return_value = [0.1, 0.2, 0.3]

    # When creating sale with multiple payment methods
    sale_items = [
        SaleItem(
            type="product",
            name="Expensive Product",
            description="High value item",
            unit_price=Decimal("100.00"),
            quantity=1,
            total=Decimal("100.00")
        )
    ]

    payment_methods = [
        PaymentMethodItem(
            method=PaymentMethod.CASH,
            amount=Decimal("50.00")
        ),
        PaymentMethodItem(
            method=PaymentMethod.CARD,
            amount=Decimal("30.00"),
            reference="CARD456"
        ),
        PaymentMethodItem(
            method=PaymentMethod.LOYALTY_POINTS,
            amount=Decimal("20.00")
        )
    ]

    sale_data = SaleRequest(
        customer_id=test_customer.id,
        items=sale_items,
        subtotal=Decimal("100.00"),
        total_amount=Decimal("100.00"),
        loyalty_points_generated=100,
        payment_methods=payment_methods
    )

    result = await create_sale(
        sale_data=sale_data,
        token=admin_token,
        db_session=session
    )

    # Then sale is created with all payment methods
    assert len(result.payment_methods) == 3
    assert result.payment_methods[0]["method"] == "cash"
    assert result.payment_methods[1]["method"] == "card"
    assert result.payment_methods[2]["method"] == "loyalty_points"