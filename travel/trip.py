from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
import flask_login
from datetime import datetime
from . import db
from .model import TripProposal, ProposalStatus, TripProposalParticipation

bp = Blueprint("trip", __name__, url_prefix="/trip")


@bp.route("/new")
@flask_login.login_required
def new_trip():
    return render_template("trip/new_trip.html")


@bp.route("/new", methods=["POST"])
@flask_login.login_required
def new_trip_post():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    destination = request.form.get("destination", "").strip()
    budget = request.form.get("budget", "").strip()
    departure_locations = request.form.get("departure_locations", "").strip()
    activities = request.form.get("activities", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    max_participants = request.form.get("max_participants", "").strip()

    if not title or not destination or not start_date or not end_date or not max_participants:
        flash("Please fill in all required fields (title, destination, dates, max participants).")
        return redirect(url_for("trip.new_trip"))

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.")
        return redirect(url_for("trip.new_trip"))

    if end_date_obj < start_date_obj:
        flash("End date must be after start date.")
        return redirect(url_for("trip.new_trip"))

    try:
        max_participants_int = int(max_participants)
        if max_participants_int <= 0:
            raise ValueError
    except ValueError:
        flash("Max participants must be a positive number.")
        return redirect(url_for("trip.new_trip"))

    budget_value = float(budget) if budget else None
    current_user = flask_login.current_user

    new_proposal = TripProposal(
        title=title,
        description=description if description else None,
        destination=destination,
        destination_final=False,
        budget=budget_value,
        budget_final=False,
        departure_locations=departure_locations if departure_locations else None,
        departure_location_final=False,
        activities=activities if activities else None,
        activities_final=False,
        start_date=start_date_obj,
        start_date_final=False,
        end_date=end_date_obj,
        end_date_final=False,
        max_participants=max_participants_int,
        status=ProposalStatus.open,
        creator_id=current_user.id,
    )

    db.session.add(new_proposal)
    db.session.commit()

    creator_participation = TripProposalParticipation(
        user_id=current_user.id, proposal_id=new_proposal.id
    )
    db.session.add(creator_participation)
    db.session.commit()

    flash("Trip proposal created successfully!")
    return redirect(url_for("trip.detail", trip_id=new_proposal.id))


@bp.route("/<int:trip_id>")
@flask_login.login_required
def detail(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    current_user = flask_login.current_user

    participation = db.session.execute(
        db.select(TripProposalParticipation).where(
            TripProposalParticipation.proposal_id == trip_id,
            TripProposalParticipation.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    is_participant = participation is not None or proposal.creator_id == current_user.id

    participants = []
    if is_participant:
        participants = (
            db.session.execute(
                db.select(TripProposalParticipation).where(
                    TripProposalParticipation.proposal_id == trip_id
                )
            ).scalars().all()
        )

    return render_template(
        "trip/detail.html",
        proposal=proposal,
        participants=participants,
        is_participant=is_participant,
    )


@bp.route("/<int:trip_id>/join", methods=["POST"])
@flask_login.login_required
def join_trip(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    user = flask_login.current_user

    already_joined = db.session.execute(
        db.select(TripProposalParticipation).where(
            TripProposalParticipation.user_id == user.id,
            TripProposalParticipation.proposal_id == trip_id,
        )
    ).scalar_one_or_none()

    if already_joined:
        flash("You are already a participant of this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    current_count = db.session.execute(
        db.select(TripProposalParticipation).where(
            TripProposalParticipation.proposal_id == trip_id
        )
    ).scalars().all()
    if len(current_count) >= proposal.max_participants:
        flash("This trip is already full.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participation = TripProposalParticipation(user_id=user.id, proposal_id=trip_id)
    db.session.add(participation)
    db.session.commit()

    flash("You have successfully joined the trip!")
    return redirect(url_for("trip.detail", trip_id=trip_id))


@bp.route("/all")
@flask_login.login_required
def list_all():
    trips = db.session.execute(db.select(TripProposal)).scalars().all()
    return render_template("trip/list.html", trips=trips)


@bp.route("/my_trips")
@flask_login.login_required
def my_trips():
    current_user = flask_login.current_user

    joined_participations = (
        db.session.execute(
            db.select(TripProposalParticipation).where(
                TripProposalParticipation.user_id == current_user.id
            )
        ).scalars().all()
    )
    joined_trips = [p.proposal for p in joined_participations]

    return render_template("trip/my_trips.html", trips=joined_trips)
