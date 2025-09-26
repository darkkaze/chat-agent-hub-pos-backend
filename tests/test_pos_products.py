"""
Feature: Product management for POS system
  As a POS operator
  I want to manage products
  So that I can maintain the product catalog

Scenario: List all active products
  Given an admin user is authenticated
  And products exist in the system
  When they request the product list
  Then the system returns all active products

Scenario: Search products by name or description
  Given an admin user is authenticated
  And products exist with different names and descriptions
  When they search for products using a query
  Then the system returns matching products

Scenario: Create new product
  Given an admin user is authenticated
  When they create a product with valid data
  Then the system creates the product successfully
  And generates embedding vector automatically

Scenario: Update existing product
  Given an admin user is authenticated
  And a product exists
  When they update the product
  Then the system updates the product successfully
  And regenerates embedding vector

Scenario: Soft delete product
  Given an admin user is authenticated
  And a product exists
  When they delete the product
  Then the system deactivates the product
  And the product is no longer listed in active products
"""

import pytest
from sqlmodel import create_engine, Session, SQLModel
from models.auth import User, Token, TokenUser, UserRole
from models.pos_models import Product
from database import get_session
from api.pos_products import (
    list_products, search_products, create_product,
    update_product, delete_product
)
from api.schemas.pos_schemas import ProductRequest
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


@pytest.mark.asyncio
async def test_list_active_products(session, admin_token):
    """Test listing all active products."""
    # Given active and inactive products exist
    active_product1 = Product(
        name="Active Product 1",
        description="This is active",
        price=Decimal("10.99"),
        is_active=True
    )
    active_product2 = Product(
        name="Active Product 2",
        description="This is also active",
        price=Decimal("15.50"),
        is_active=True
    )
    inactive_product = Product(
        name="Inactive Product",
        description="This is inactive",
        price=Decimal("5.00"),
        is_active=False
    )
    session.add_all([active_product1, active_product2, inactive_product])
    session.commit()

    # When listing products
    result = await list_products(
        token=admin_token,
        db_session=session
    )

    # Then return only active products
    assert len(result.products) == 2
    product_names = [p.name for p in result.products]
    assert "Active Product 1" in product_names
    assert "Active Product 2" in product_names
    assert "Inactive Product" not in product_names


@pytest.mark.asyncio
async def test_search_products_by_name(session, admin_token):
    """Test searching products by name."""
    # Given products with different names
    product1 = Product(
        name="Coffee Maker",
        description="Makes great coffee",
        price=Decimal("99.99"),
        is_active=True
    )
    product2 = Product(
        name="Tea Kettle",
        description="Perfect for tea lovers",
        price=Decimal("45.00"),
        is_active=True
    )
    session.add_all([product1, product2])
    session.commit()

    # When searching by name
    result = await search_products(
        q="coffee",
        token=admin_token,
        db_session=session
    )

    # Then return matching product
    assert len(result.products) == 1
    assert result.products[0].name == "Coffee Maker"


@pytest.mark.asyncio
async def test_search_products_by_description(session, admin_token):
    """Test searching products by description."""
    # Given products with different descriptions
    product1 = Product(
        name="Coffee Maker",
        description="Makes great coffee",
        price=Decimal("99.99"),
        is_active=True
    )
    product2 = Product(
        name="Tea Kettle",
        description="Perfect for tea lovers",
        price=Decimal("45.00"),
        is_active=True
    )
    session.add_all([product1, product2])
    session.commit()

    # When searching by description
    result = await search_products(
        q="tea lovers",
        token=admin_token,
        db_session=session
    )

    # Then return matching product
    assert len(result.products) == 1
    assert result.products[0].name == "Tea Kettle"


@pytest.mark.asyncio
@patch('api.pos_products.generate_embedding')
async def test_create_product_with_embedding(mock_embedding, session, admin_token):
    """Test creating a product with automatic embedding generation."""
    # Given embedding generation returns a vector
    mock_embedding.return_value = [0.1, 0.2, 0.3]

    # When creating a product
    product_data = ProductRequest(
        name="New Product",
        description="A brand new product",
        price=Decimal("25.99")
    )

    result = await create_product(
        product_data=product_data,
        token=admin_token,
        db_session=session
    )

    # Then product is created successfully
    assert result.name == "New Product"
    assert result.description == "A brand new product"
    assert result.price == Decimal("25.99")
    assert result.is_active == True
    assert result.id.startswith("product_")

    # And embedding generation was called
    mock_embedding.assert_called_once_with("New Product A brand new product")


@pytest.mark.asyncio
@patch('api.pos_products.generate_embedding')
async def test_create_product_without_embedding(mock_embedding, session, admin_token):
    """Test creating a product when embedding generation fails."""
    # Given embedding generation returns None
    mock_embedding.return_value = None

    # When creating a product
    product_data = ProductRequest(
        name="New Product",
        description="A brand new product",
        price=Decimal("25.99")
    )

    result = await create_product(
        product_data=product_data,
        token=admin_token,
        db_session=session
    )

    # Then product is still created successfully
    assert result.name == "New Product"
    assert result.is_active == True


@pytest.mark.asyncio
@patch('api.pos_products.generate_embedding')
async def test_update_product(mock_embedding, session, admin_token):
    """Test updating a product."""
    # Given embedding regeneration returns a new vector
    mock_embedding.return_value = [0.4, 0.5, 0.6]

    # And a product exists
    product = Product(
        name="Old Product",
        description="Old description",
        price=Decimal("10.00"),
        is_active=True
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    # When updating the product
    product_data = ProductRequest(
        name="Updated Product",
        description="Updated description",
        price=Decimal("15.50")
    )

    result = await update_product(
        product_id=product.id,
        product_data=product_data,
        token=admin_token,
        db_session=session
    )

    # Then product is updated successfully
    assert result.id == product.id
    assert result.name == "Updated Product"
    assert result.description == "Updated description"
    assert result.price == Decimal("15.50")

    # And embedding regeneration was called
    mock_embedding.assert_called_once_with("Updated Product Updated description")


@pytest.mark.asyncio
async def test_soft_delete_product(session, admin_token):
    """Test soft deleting a product."""
    # Given a product exists
    product = Product(
        name="Product to Delete",
        description="This will be deleted",
        price=Decimal("20.00"),
        is_active=True
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    # When deleting the product
    result = await delete_product(
        product_id=product.id,
        token=admin_token,
        db_session=session
    )

    # Then product is deactivated
    assert "deactivated successfully" in result.message

    # And product is not active anymore
    updated_product = session.get(Product, product.id)
    assert updated_product.is_active == False

    # And product doesn't appear in active list
    active_list = await list_products(
        token=admin_token,
        db_session=session
    )
    assert len(active_list.products) == 0


@pytest.mark.asyncio
async def test_product_not_found_errors(session, admin_token):
    """Test error handling for non-existent products."""
    # When updating non-existent product
    product_data = ProductRequest(
        name="Non-existent",
        description="Does not exist",
        price=Decimal("10.00")
    )

    # Then raise 404 error
    with pytest.raises(Exception) as exc_info:
        await update_product(
            product_id="nonexistent_id",
            product_data=product_data,
            token=admin_token,
            db_session=session
        )
    assert "404" in str(exc_info.value)

    # When deleting non-existent product
    with pytest.raises(Exception) as exc_info:
        await delete_product(
            product_id="nonexistent_id",
            token=admin_token,
            db_session=session
        )
    assert "404" in str(exc_info.value)