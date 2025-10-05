from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from database import get_session
from models.auth import Token
from models.pos_models import SaleSignal
from .schemas.pos_schemas import (
    SignalRequest, SignalResponse, SignalListResponse,
    SignalTestResponse, MessageResponse
)
from helpers.auth import get_auth_token, require_admin_or_agent
from helpers.signal_notifier import test_signal
from datetime import datetime, timezone


router = APIRouter(prefix="/signals", tags=["pos_signals"])


@router.post("/", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
async def create_signal(
    signal_data: SignalRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Create new signal for sale notifications."""
    await require_admin_or_agent(token, db_session)

    new_signal = SaleSignal(
        name=signal_data.name,
        url=signal_data.url,
        is_active=signal_data.is_active if signal_data.is_active is not None else True,
        auth_config=signal_data.auth_config or "{}",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db_session.add(new_signal)
    db_session.commit()
    db_session.refresh(new_signal)

    return SignalResponse(
        id=new_signal.id,
        name=new_signal.name,
        url=new_signal.url,
        is_active=new_signal.is_active,
        auth_config=new_signal.auth_config,
        created_at=new_signal.created_at,
        updated_at=new_signal.updated_at
    )


@router.get("/", response_model=SignalListResponse)
async def list_signals(
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """List all signals."""
    await require_admin_or_agent(token, db_session)

    statement = select(SaleSignal).order_by(SaleSignal.created_at.desc())
    signals = db_session.exec(statement).all()

    signal_responses = [
        SignalResponse(
            id=signal.id,
            name=signal.name,
            url=signal.url,
            is_active=signal.is_active,
            auth_config=signal.auth_config,
            created_at=signal.created_at,
            updated_at=signal.updated_at
        )
        for signal in signals
    ]

    return SignalListResponse(signals=signal_responses)


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Get signal details."""
    await require_admin_or_agent(token, db_session)

    signal = db_session.get(SaleSignal, signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )

    return SignalResponse(
        id=signal.id,
        name=signal.name,
        url=signal.url,
        is_active=signal.is_active,
        auth_config=signal.auth_config,
        created_at=signal.created_at,
        updated_at=signal.updated_at
    )


@router.put("/{signal_id}", response_model=SignalResponse)
async def update_signal(
    signal_id: str,
    signal_data: SignalRequest,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Update signal."""
    await require_admin_or_agent(token, db_session)

    signal = db_session.get(SaleSignal, signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )

    signal.name = signal_data.name
    signal.url = signal_data.url
    signal.is_active = signal_data.is_active if signal_data.is_active is not None else signal.is_active
    signal.auth_config = signal_data.auth_config or "{}"
    signal.updated_at = datetime.now(timezone.utc)

    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)

    return SignalResponse(
        id=signal.id,
        name=signal.name,
        url=signal.url,
        is_active=signal.is_active,
        auth_config=signal.auth_config,
        created_at=signal.created_at,
        updated_at=signal.updated_at
    )


@router.delete("/{signal_id}", response_model=MessageResponse)
async def delete_signal(
    signal_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Delete signal (hard delete)."""
    await require_admin_or_agent(token, db_session)

    signal = db_session.get(SaleSignal, signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )

    db_session.delete(signal)
    db_session.commit()

    return MessageResponse(message="Signal deleted successfully")


@router.post("/{signal_id}/test", response_model=SignalTestResponse)
async def test_signal_endpoint(
    signal_id: str,
    token: Token = Depends(get_auth_token),
    db_session: Session = Depends(get_session)
):
    """Test signal with dummy sale data."""
    await require_admin_or_agent(token, db_session)

    signal = db_session.get(SaleSignal, signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )

    result = await test_signal(signal)

    return SignalTestResponse(
        success=result["success"],
        status_code=result["status_code"],
        response_body=result["response_body"],
        error=result["error"]
    )
