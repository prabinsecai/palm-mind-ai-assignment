import pytest
from pydantic import ValidationError
from app.schemas.chat import ChatRequest, BookingDetails

def test_chat_validation():
    with pytest.raises(ValidationError): ChatRequest(session_id="",message="hello")

def test_booking_validation():
    b=BookingDetails(name="Jane",email="jane@example.com",date="2026-10-01",time="10:30"); assert b.email=="jane@example.com"
