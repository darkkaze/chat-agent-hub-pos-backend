import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from api import pos_customers, pos_products, pos_sales, pos_staff

app = FastAPI(
    title="Agent Hub POS API",
    version="1.0.0",
    docs_url="/pos/api/docs",
    redoc_url="/pos/api/redoc"
)

# CORS middleware for development
if os.getenv("ENVIRONMENT", "development") == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

app.include_router(pos_customers.router, prefix="/pos/api")
app.include_router(pos_products.router, prefix="/pos/api")
app.include_router(pos_sales.router, prefix="/pos/api")
app.include_router(pos_staff.router, prefix="/pos/api")


@app.get("/pos/api/health")
async def root():
    """API health check."""
    return {"message": "Agent Hub POS API is running"}