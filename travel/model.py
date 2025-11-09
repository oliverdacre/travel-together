import datetime
from typing import List, Optional

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import db
import enum

class ProposalStatus(enum.Enum):
    open = 1
    closed_to_new_participants = 2
    finalized = 3
    cancelled = 4

class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_trip_proposals: Mapped[List["TripProposal"]] = relationship("TripProposal", back_populates="creator")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="user")
    participations: Mapped[List["TripProposalParticipation"]] = relationship(
        "TripProposalParticipation", back_populates="user"
    )

class TripProposal(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    budget: Mapped[Optional[float]] = mapped_column(nullable=True)
    budget_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    departure_locations: Mapped[Optional[List[str]]] = mapped_column(String(200), nullable=True)
    departure_location_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    activities: Mapped[Optional[List[str]]] = mapped_column(String(200), nullable=True)
    activities_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    start_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    start_date_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    end_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_date_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    max_participants: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(nullable=False, default=ProposalStatus.open)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    creator: Mapped["User"] = relationship("User", back_populates="created_trip_proposals")
    meetups: Mapped[List["Meetup"]] = relationship("Meetup", back_populates="proposal")
    participants: Mapped[List["TripProposalParticipation"]] = relationship(
        "TripProposalParticipation", back_populates="proposal"
    )
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="proposal")

class TripProposalParticipation(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    user = relationship("User", back_populates="participations")
    proposal = relationship("TripProposal", back_populates="participants")

class Meetup(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    proposal = relationship("TripProposal", back_populates="meetups")

class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(String(1000), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)

    user = relationship("User", back_populates="messages")
    proposal = relationship("TripProposal", back_populates="messages")