from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from models.pos_models import PaymentMethod


# Staff Schemas
class StaffRequest(BaseModel):
    """Schema for creating/updating staff."""
    name: str = Field(..., description="Staff member name")
    schedule: Optional[str] = Field(default="{}", description="Staff schedule as JSON string")


class StaffResponse(BaseModel):
    """Schema for staff response."""
    id: str = Field(..., description="Staff ID")
    name: str = Field(..., description="Staff member name")
    schedule: str = Field(..., description="Staff schedule as JSON string")
    is_active: bool = Field(..., description="Staff active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class StaffListResponse(BaseModel):
    """Schema for staff list response."""
    staff: List[StaffResponse] = Field(..., description="List of staff members")


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
    details: Optional[str] = Field(default=None, description="Additional notes")
    price: Decimal = Field(..., description="Product price")
    variable_price: Optional[bool] = Field(default=False, description="If price is editable in cart")
    category: Optional[str] = Field(default=None, description="Product category")
    meta_data: Optional[str] = Field(default="{}", description="JSON metadata")


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    details: Optional[str] = Field(default=None, description="Additional notes")
    price: Decimal = Field(..., description="Product price")
    variable_price: bool = Field(..., description="If price is editable in cart")
    category: Optional[str] = Field(default=None, description="Product category")
    meta_data: str = Field(..., description="JSON metadata")
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
    staff_id: str = Field(..., description="Staff ID")
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
    staff_id: str = Field(..., description="Staff ID")
    customer: Optional[CustomerResponse] = Field(default=None, description="Customer information")
    staff: Optional[StaffResponse] = Field(default=None, description="Staff information")
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


# Webhook Schemas
class WebhookRequest(BaseModel):
    """Schema for creating/updating webhook."""
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Webhook URL to call")
    is_active: Optional[bool] = Field(default=True, description="Webhook active status")
    auth_config: Optional[str] = Field(default="{}", description="JSON auth config")


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: str = Field(..., description="Webhook ID")
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Webhook URL")
    is_active: bool = Field(..., description="Webhook active status")
    auth_config: str = Field(..., description="JSON auth config")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WebhookListResponse(BaseModel):
    """Schema for webhook list response."""
    webhooks: List[WebhookResponse] = Field(..., description="List of webhooks")


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""
    success: bool = Field(..., description="Test success status")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    response_body: Optional[str] = Field(default=None, description="Response body")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# Message Schemas
class MessageResponse(BaseModel):
    """Schema for API response messages."""
    message: str = Field(..., description="Response message")