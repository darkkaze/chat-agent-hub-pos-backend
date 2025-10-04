from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from database import get_session
from models.auth import Token
from models.pos_models import Product
from .schemas.pos_schemas import (
    ProductRequest, ProductResponse, ProductSearchResponse, MessageResponse
)
from helpers.auth import get_auth_token, require_admin_or_agent
from datetime import datetime, timezone
import json
router = APIRouter(prefix="/products", tags=["pos_products"])


@router.get("/", response_model=ProductSearchResponse)
async def list_products(
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """List all active products."""
    await require_admin_or_agent(token, db_session)

    statement = select(Product).where(Product.is_active == True).order_by(Product.name)
    products = db_session.exec(statement).all()

    product_responses = [
        ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            details=product.details,
            price=product.price,
            variable_price=product.variable_price,
            category=product.category,
            meta_data=product.meta_data,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at
        )
        for product in products
    ]

    return ProductSearchResponse(products=product_responses)


@router.get("/search", response_model=ProductSearchResponse)
async def search_products(
    q: str = Query(..., description="Search query for product name and description"),
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Search products using full-text search on name and description."""
    await require_admin_or_agent(token, db_session)

    # Full-text search using LIKE on name and description
    statement = select(Product).where(
        (Product.name.like(f'%{q}%') | Product.description.like(f'%{q}%')) &
        (Product.is_active == True)
    ).order_by(Product.name)

    products = db_session.exec(statement).all()

    # TODO: Implement vector similarity search when embedding_vector is available
    # For now, return full-text search results

    product_responses = [
        ProductResponse(
            id=product.id,
            name=product.name,
            description=product.description,
            details=product.details,
            price=product.price,
            variable_price=product.variable_price,
            category=product.category,
            meta_data=product.meta_data,
            is_active=product.is_active,
            created_at=product.created_at,
            updated_at=product.updated_at
        )
        for product in products
    ]

    return ProductSearchResponse(products=product_responses)


@router.post("/", response_model=ProductResponse)
async def create_product(
    product_data: ProductRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Create new product with automatic embedding generation."""
    await require_admin_or_agent(token, db_session)

    # TODO: Generate embedding for search when vector search is implemented
    # embedding_text = f"{product_data.name} {product_data.description or ''}"
    # embedding_vector = await generate_embedding(embedding_text)

    new_product = Product(
        name=product_data.name,
        description=product_data.description,
        details=product_data.details,
        price=product_data.price,
        variable_price=product_data.variable_price or False,
        category=product_data.category,
        meta_data=product_data.meta_data or "{}",
        is_active=True,
        embedding_vector=None,  # Vector search disabled for now
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db_session.add(new_product)
    db_session.commit()
    db_session.refresh(new_product)

    return ProductResponse(
        id=new_product.id,
        name=new_product.name,
        description=new_product.description,
        details=new_product.details,
        price=new_product.price,
        variable_price=new_product.variable_price,
        category=new_product.category,
        meta_data=new_product.meta_data,
        is_active=new_product.is_active,
        created_at=new_product.created_at,
        updated_at=new_product.updated_at
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Update product and regenerate embedding vector."""
    await require_admin_or_agent(token, db_session)

    product = db_session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Update product data
    if product_data.name is not None:
        product.name = product_data.name
    if product_data.description is not None:
        product.description = product_data.description
    if product_data.details is not None:
        product.details = product_data.details
    if product_data.price is not None:
        product.price = product_data.price
    if product_data.variable_price is not None:
        product.variable_price = product_data.variable_price
    if product_data.category is not None:
        product.category = product_data.category
    if product_data.meta_data is not None:
        product.meta_data = product_data.meta_data

    product.updated_at = datetime.now(timezone.utc)

    # TODO: Regenerate embedding when vector search is implemented
    # embedding_text = f"{product_data.name} {product_data.description or ''}"
    # embedding_vector = await generate_embedding(embedding_text)
    product.embedding_vector = None  # Vector search disabled for now

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        details=product.details,
        price=product.price,
        variable_price=product.variable_price,
        category=product.category,
        meta_data=product.meta_data,
        is_active=product.is_active,
        created_at=product.created_at,
        updated_at=product.updated_at
    )


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Soft delete product by setting is_active=False."""
    await require_admin_or_agent(token, db_session)

    product = db_session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    product.is_active = False
    product.updated_at = datetime.now(timezone.utc)

    db_session.add(product)
    db_session.commit()

    return MessageResponse(message=f"Product {product.name} deactivated successfully")