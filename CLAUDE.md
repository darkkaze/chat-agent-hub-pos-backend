# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

FastAPI backend for Agent Hub POS system that manages point of sale operations, product catalog, customer management, and sales transactions.

### Core Components

**FastAPI Application (`main.py`)**
- Main application entry point with all API routers
- POS-specific endpoints for products, customers, and sales

**Database Layer (`database.py`)**
- SQLModel with SQLite backend (`pos.db`)
- Dependency injection: `session: Session = Depends(get_session)`
- Management commands in `manage.py` for database operations

**Models (`models/`)**
- Custom ID generation: `{prefix}_{10_random_chars}` using `id_generator()`
- POS-specific models for products, customers, sales, and inventory

### Key Models

**Authentication:**
- `User`: POS operators (ADMIN/CASHIER roles)
- `Token`: Session management for POS users

**POS Operations:**
- `Product`: Product catalog with pricing and inventory
- `Customer`: Customer information with loyalty points
- `Sale`: Complete sale transactions with items and payment methods
- Item management with quantity tracking

**Core POS Features:**
- Product catalog management (CRUD operations)
- Customer database with phone-based lookup
- Sales processing with multiple payment methods
- Loyalty points system integration
- Real-time inventory tracking

## Development Setup

**Initial Setup:**

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database tables
python manage.py init_db

# Create first admin user
python manage.py create_admin admin password123

# Check database status
python manage.py check_db
```

**Required Services:**

Start these services in separate terminals:

```bash
# Terminal 1: FastAPI server
source .venv/bin/activate
fastapi dev main.py

# Terminal 2: Celery worker (if needed)
source .venv/bin/activate
celery -A worker worker --loglevel=info
```

## API Structure

**Core Endpoints:**
- `/products` - Product catalog management (CRUD)
- `/customers` - Customer management and lookup
- `/sales` - Sales transaction processing
- `/sales/history` - Sales history with pagination

**Key Features:**
- Product management with active/inactive status
- Customer lookup by phone number
- Multi-item sales with quantity tracking
- Multiple payment methods (cash, card, transfer, loyalty points)
- Loyalty points calculation and redemption
- Sales history with pagination and search

**POS Workflow:**
1. Product selection and cart management
2. Customer identification (optional)
3. Payment method selection (multiple methods supported)
4. Sale completion and loyalty points processing
5. Receipt generation and inventory update

## Testing

Test APIs directly using SQLite in-memory fixtures. Mock external dependencies.

```python
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
```

## POS Business Logic

**Sale Processing:**
- Validate product availability and pricing
- Calculate subtotals, discounts, and totals
- Process multiple payment methods
- Update inventory levels
- Generate loyalty points based on purchase amount
- Store complete transaction history

**Customer Management:**
- Phone-based customer lookup
- Loyalty points tracking and redemption
- Purchase history association
- Optional customer information storage