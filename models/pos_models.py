from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from decimal import Decimal
from .helper import id_generator
import json

if TYPE_CHECKING:
    pass


class PaymentMethod(str, Enum):
    """Available payment methods for POS sales."""
    ADVANCE_TRANSFER = "advance_transfer"
    ADVANCE_CASH = "advance_cash"
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    LOYALTY_POINTS = "loyalty_points"


class Staff(SQLModel, table=True):
    """Modelo para personal del punto de venta."""
    id: str = Field(default_factory=id_generator('staff', 10), primary_key=True)
    name: str = Field(index=True)
    schedule: str = Field(default="{}")  # JSON string for schedule/shifts
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    sales: List["Sale"] = Relationship(back_populates="staff")

    def get_schedule(self) -> dict:
        """Parse schedule JSON string to Python dict."""
        return json.loads(self.schedule) if self.schedule else {}

    def set_schedule(self, schedule: dict):
        """Set schedule from Python dict to JSON string."""
        self.schedule = json.dumps(schedule)


class Customer(SQLModel, table=True):
    """Modelo para clientes del punto de venta. No incluye vectores embedding ya que no requiere análisis semántico."""
    id: str = Field(default_factory=id_generator('customer', 10), primary_key=True)
    phone: str = Field(unique=True, index=True)
    name: Optional[str] = Field(default=None)
    loyalty_points: Decimal = Field(default=Decimal("0.00"))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    sales: List["Sale"] = Relationship(back_populates="customer")


class Product(SQLModel, table=True):
    """Modelo para productos del catálogo. embedding_vector: Vector semántico generado automáticamente al crear/actualizar usando name + description para búsquedas inteligentes. Se llena mediante proceso automático usando OpenAI embeddings."""
    id: str = Field(default_factory=id_generator('product', 10), primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    price: Decimal
    is_active: bool = Field(default=True)
    embedding_vector: Optional[str] = Field(default=None)  # JSON string of vector array
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sale(SQLModel, table=True):
    """Modelo para ventas del POS. embedding_vector: Vector generado automáticamente al crear usando contenido de items para análisis de patrones de compra y recomendaciones. Se llena automáticamente usando OpenAI embeddings."""
    id: str = Field(default_factory=id_generator('sale', 10), primary_key=True)
    customer_id: str = Field(foreign_key="customer.id", index=True)
    staff_id: str = Field(foreign_key="staff.id", index=True)
    items: str = Field()  # JSON string of items array
    subtotal: Decimal
    discount_amount: Decimal = Field(default=Decimal("0.00"))
    total_amount: Decimal
    loyalty_points_generated: int = Field(default=0)
    payment_methods: str = Field()  # JSON string of payment methods array
    embedding_vector: Optional[str] = Field(default=None)  # JSON string of vector array
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    customer: Optional[Customer] = Relationship(back_populates="sales")
    staff: Optional[Staff] = Relationship(back_populates="sales")

    def get_items(self) -> List[dict]:
        """Parse items JSON string to Python list."""
        return json.loads(self.items) if self.items else []

    def set_items(self, items: List[dict]):
        """Set items from Python list to JSON string."""
        self.items = json.dumps(items)

    def get_payment_methods(self) -> List[dict]:
        """Parse payment_methods JSON string to Python list."""
        return json.loads(self.payment_methods) if self.payment_methods else []

    def set_payment_methods(self, payment_methods: List[dict]):
        """Set payment_methods from Python list to JSON string."""
        self.payment_methods = json.dumps(payment_methods)

    def get_embedding_vector(self) -> Optional[List[float]]:
        """Parse embedding_vector JSON string to Python list."""
        return json.loads(self.embedding_vector) if self.embedding_vector else None

    def set_embedding_vector(self, vector: List[float]):
        """Set embedding_vector from Python list to JSON string."""
        self.embedding_vector = json.dumps(vector)