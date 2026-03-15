import datetime
import enum
import uuid

from sqlalchemy import BigInteger, Date, Enum, Integer, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UserQuizStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    GIVEUP = "GIVEUP"


class Base(DeclarativeBase):
    pass


class UserQuizResult(Base):
    __tablename__ = "user_quiz_results"
    __table_args__ = (
        UniqueConstraint("user_id", "quiz_date", name="uq_user_quiz_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    quiz_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[UserQuizStatus] = mapped_column(
        Enum(UserQuizStatus), nullable=False, default=UserQuizStatus.FAIL
    )
    guess_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_count: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class OutageDate(Base):
    __tablename__ = "outage_dates"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
