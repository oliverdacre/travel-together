import datetime
from typing import List, Optional

import flask_login
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from . import db
import enum

class ProposalStatus(enum.Enum):
    open = "Open"
    closed = "Closed to New Participants"
    finalized = "Finalized"
    cancelled = "Cancelled"

class User(flask_login.UserMixin, db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_trip_proposals: Mapped[List["TripProposal"]] = relationship("TripProposal", back_populates="creator")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="user")
    participations: Mapped[List["TripProposalParticipation"]] = relationship(
        "TripProposalParticipation", back_populates="user"
    )

    received_ratings: Mapped[List["UserRating"]] = relationship(
        "UserRating", foreign_keys="[UserRating.ratee_id]", back_populates="ratee"
    )
    given_ratings: Mapped[List["UserRating"]] = relationship(
        "UserRating", foreign_keys="[UserRating.rater_id]", back_populates="rater"
    )

    @property
    def average_rating(self) -> Optional[float]:
        if not self.received_ratings:
            return None
        return sum(r.rating for r in self.received_ratings) / len(self.received_ratings)

class TripProposal(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    budget: Mapped[Optional[float]] = mapped_column(nullable=True)
    budget_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    departure_locations: Mapped[Optional[List[str]]] = mapped_column(String(200), nullable=True)
    departure_locations_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    activities: Mapped[Optional[List[str]]] = mapped_column(String(200), nullable=True)
    activities_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    start_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    start_date_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    end_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    end_date_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    max_participants: Mapped[int] = mapped_column(nullable=False)
    max_participants_final: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(nullable=False, default=ProposalStatus.open)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    images: Mapped[List["Image"]] = relationship("Image", back_populates="proposal")
    
    creator: Mapped["User"] = relationship("User", back_populates="created_trip_proposals")
    meetups: Mapped[List["Meetup"]] = relationship("Meetup", back_populates="proposal")
    participants: Mapped[List["TripProposalParticipation"]] = relationship(
        "TripProposalParticipation", back_populates="proposal"
    )
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="proposal")

    @property
    def editors(self):
        return [p.user for p in self.participants if p.is_editor]
    
    ratings: Mapped[List["UserRating"]] = relationship(
        "UserRating", back_populates="trip"
    )


class TripProposalParticipation(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    is_editor: Mapped[bool] = mapped_column(nullable=False, default=False)

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
    images: Mapped[List["Image"]] = relationship("Image", back_populates="message")
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)

    user = relationship("User", back_populates="messages")
    proposal = relationship("TripProposal", back_populates="messages")


class Image(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    message_id: Mapped[int] = mapped_column(ForeignKey("message.id"), nullable=False)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)

    message = relationship("Message", back_populates="images")
    proposal = relationship("TripProposal", back_populates="images")


class UserRating(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)

    trip_id: Mapped[int] = mapped_column(ForeignKey("trip_proposal.id"), nullable=False)
    rater_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    ratee_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    rating: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    trip = relationship("TripProposal", back_populates="ratings")
    rater = relationship("User", foreign_keys=[rater_id], back_populates="given_ratings")
    ratee = relationship("User", foreign_keys=[ratee_id], back_populates="received_ratings")