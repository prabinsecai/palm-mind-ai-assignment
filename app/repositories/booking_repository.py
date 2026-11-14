from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Booking


class BookingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, name: str, email: str, date: str, time: str) -> Booking:
        booking = Booking(
            name=name,
            email=email,
            interview_date=date,
            interview_time=time,
        )
        self.db.add(booking)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.db.scalar(
                select(Booking).where(
                    Booking.email == email,
                    Booking.interview_date == date,
                    Booking.interview_time == time,
                )
            )
            if existing is not None:
                return existing
            raise
        await self.db.refresh(booking)
        return booking
