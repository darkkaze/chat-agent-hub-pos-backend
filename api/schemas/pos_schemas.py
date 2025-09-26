from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from models.pos_models import PaymentMethod


# Customer Schemas
class CustomerRequest(BaseModel):
    """Schema for creating/updating customer."""
    phone: str = Field(..., description="Customer phone number")
    name: Optional[str] = Field(default=None, description="Customer name")


class CustomerResponse(BaseModel):
    """Schema for customer response."""
    id: str = Field(..., description="Customer ID")
    phone: str = Field(..., description="Customer phone number")
    name: Optional[str] = Field(default=None, description="Customer name")
    loyalty_points: Decimal = Field(..., description="Customer loyalty points")
    is_active: bool = Field(..., description="Customer active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class CustomerWalletRequest(BaseModel):
    """Schema for updating customer wallet."""
    loyalty_points: Decimal = Field(..., description="New loyalty points amount")


class CustomerSearchResponse(BaseModel):
    """Schema for customer search response."""
    customers: List[CustomerResponse] = Field(..., description="List of matching customers")


# Product Schemas
class ProductRequest(BaseModel):
    """Schema for creating/updating product."""
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    price: Decimal = Field(..., description="Product price")


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    price: Decimal = Field(..., description="Product price")
    is_active: bool = Field(..., description="Product active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ProductSearchResponse(BaseModel):
    """Schema for product search response."""
    products: List[ProductResponse] = Field(..., description="List of matching products")


# Sale Item Schemas
class SaleItemBase(BaseModel):
    """Base schema for sale items."""
    type: str = Field(..., description="Item type: product, other, discount")
    product_id: Optional[str] = Field(default=None, description="Product ID if type is product")
    name: str = Field(..., description="Item name")
    description: str = Field(..., description="Item description")
    unit_price: Decimal = Field(..., description="Unit price")
    quantity: int = Field(..., description="Quantity")
    total: Decimal = Field(..., description="Total amount")


class SaleItemDiscount(SaleItemBase):
    """Schema for discount sale items."""
    discount_type: str = Field(..., description="Discount type: percentage, fixed")
    discount_value: Decimal = Field(..., description="Discount value")
    applied_to_amount: Decimal = Field(..., description="Amount discount was applied to")


class SaleItem(BaseModel):
    """Schema for sale items (union of base and discount)."""
    type: str = Field(..., description="Item type: product, other, discount")
    product_id: Optional[str] = Field(default=None, description="Product ID if type is product")
    name: str = Field(..., description="Item name")
    description: str = Field(..., description="Item description")
    unit_price: Decimal = Field(..., description="Unit price")
    quantity: int = Field(..., description="Quantity")
    total: Decimal = Field(..., description="Total amount")
    discount_type: Optional[str] = Field(default=None, description="Discount type: percentage, fixed")
    discount_value: Optional[Decimal] = Field(default=None, description="Discount value")
    applied_to_amount: Optional[Decimal] = Field(default=None, description="Amount discount was applied to")


# Payment Method Schemas
class PaymentMethodItem(BaseModel):
    """Schema for payment method items."""
    method: PaymentMethod = Field(..., description="Payment method")
    amount: Decimal = Field(..., description="Payment amount")
    reference: Optional[str] = Field(default=None, description="Payment reference")


# Sale Schemas
class SaleRequest(BaseModel):
    """Schema for creating sale."""
    customer_id: str = Field(..., description="Customer ID")
    items: List[SaleItem] = Field(..., description="Sale items")
    subtotal: Decimal = Field(..., description="Subtotal before discounts")
    discount_amount: Decimal = Field(default=Decimal("0.00"), description="Total discount amount")
    total_amount: Decimal = Field(..., description="Final total amount")
    loyalty_points_generated: int = Field(default=0, description="Loyalty points generated")
    payment_methods: List[PaymentMethodItem] = Field(..., description="Payment methods used")

    @validator('payment_methods')
    def validate_payment_methods(cls, v, values):
        """Validate that payment methods sum equals total amount."""
        if 'total_amount' in values:
            total_payments = sum(pm.amount for pm in v)
            if abs(total_payments - values['total_amount']) > Decimal('0.01'):
                raise ValueError('Payment methods sum must equal total amount')
        return v


class SaleResponse(BaseModel):
    """Schema for sale response."""
    id: str = Field(..., description="Sale ID")
    customer_id: str = Field(..., description="Customer ID")
    customer: Optional[CustomerResponse] = Field(default=None, description="Customer information")
    items: List[SaleItem] = Field(..., description="Sale items")
    subtotal: Decimal = Field(..., description="Subtotal before discounts")
    discount_amount: Decimal = Field(..., description="Total discount amount")
    total_amount: Decimal = Field(..., description="Final total amount")
    loyalty_points_generated: int = Field(..., description="Loyalty points generated")
    payment_methods: List[PaymentMethodItem] = Field(..., description="Payment methods used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SaleListResponse(BaseModel):
    """Schema for sale list response."""
    sales: List[SaleResponse] = Field(..., description="List of sales")
    total: int = Field(..., description="Total number of sales")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


# Message Schemas
class MessageResponse(BaseModel):
    """Schema for API response messages."""
    message: str = Field(..., description="Response message")