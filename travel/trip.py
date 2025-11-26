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
        description_final=False,
        destination=destination,
        destination_final=False,
        budget=budget_value,
        budget_final=False,
        departure_locations=departure_locations if departure_locations else None,
        departure_locations_final=False,
        activities=activities if activities else None,
        activities_final=False,
        start_date=start_date_obj,
        start_date_final=False,
        end_date=end_date_obj,
        end_date_final=False,
        max_participants=max_participants_int,
        max_participants_final=False,
        status=ProposalStatus.open,
        creator_id=current_user.id,
    )

    db.session.add(new_proposal)
    db.session.commit()

    creator_participation = TripProposalParticipation(
        user_id=current_user.id, proposal_id=new_proposal.id, is_editor=True
    )
    db.session.add(creator_participation)
    db.session.commit()

    if new_proposal.max_participants == 1:
        new_proposal.status = ProposalStatus.closed_to_new_participants
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
        proposal.status = ProposalStatus.closed_to_new_participants
        db.session.commit()
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
    query = db.select(TripProposal).where(TripProposal.status == ProposalStatus.open)
    trips = db.session.execute(query).scalars().all()
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


@bp.route("/<int:trip_id>/edit")
@flask_login.login_required
def edit_trip(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)

    if flask_login.current_user not in proposal.editors:
        flash("You do not have permission to edit this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    return render_template("trip/edit_trip.html", proposal=proposal)


@bp.route("/<int:trip_id>/edit", methods=["POST"])
@flask_login.login_required
def edit_trip_post(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)

    if flask_login.current_user not in proposal.editors:
        flash("You do not have permission to edit this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    description = request.form.get("description", "").strip()
    destination = request.form.get("destination", "").strip()
    budget = request.form.get("budget", "").strip()
    departure_locations = request.form.get("departure_locations", "").strip()
    activities = request.form.get("activities", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    max_participants = request.form.get("max_participants", "").strip()

    if not destination or not start_date or not end_date or not max_participants:
        flash("Please fill in all required fields (destination, dates, max participants).")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date format. Use YYYY-MM-DD.")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    if end_date_obj < start_date_obj:
        flash("End date must be after start date.")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    try:
        max_participants_int = int(max_participants)
        if max_participants_int <= 0:
            raise ValueError
    except ValueError:
        flash("Max participants must be a positive number.")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    budget_value = float(budget) if budget else None

    proposal.description = description if description else None
    proposal.destination = destination
    proposal.budget = budget_value
    proposal.departure_locations = departure_locations if departure_locations else None
    proposal.activities = activities if activities else None
    proposal.start_date = start_date_obj
    proposal.end_date = end_date_obj
    proposal.max_participants = max_participants_int

    db.session.commit()
    flash("Trip proposal updated successfully!")
    return redirect(url_for("trip.detail", trip_id=trip_id))

    
@bp.route("/<int:trip_id>/add_editor", methods=["POST"])
@flask_login.login_required
def add_editor(trip_id):

    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in proposal.editors:
        abort(403)

    user_id = request.form.get("user_id")

    if not user_id:
        flash("No user selected.", "danger")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participation = TripProposalParticipation.query.filter_by(
        proposal_id=trip_id,
        user_id=user_id
    ).first()

    if not participation:
        flash("The selected user is not a participant.", "danger")
        return redirect(url_for("trip.detail", trip_id=trip_id))
    if participation.is_editor:
        flash("This user is already an editor.", "warning")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participation.is_editor = True
    db.session.commit()

    flash("User has been granted editor permissions!", "success")
    return redirect(url_for("trip.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/finalize", methods=["POST"])
@flask_login.login_required
def finalize_proposal(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in proposal.editors:
        abort(403)

    proposal.description_final = True
    proposal.destination_final = True
    proposal.budget_final = True
    proposal.departure_locations_final = True
    proposal.activities_final = True
    proposal.start_date_final = True
    proposal.end_date_final = True
    proposal.max_participants_final = True
    proposal.status = ProposalStatus.finalized

    db.session.commit()

    flash("Trip proposal has been finalized!", "success")
    return redirect(url_for("trip.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/close", methods=["POST"])
@flask_login.login_required
def close_proposal(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in proposal.editors:
        abort(403)

    proposal.status = ProposalStatus.closed
    db.session.commit()

    flash("Trip proposal has been closed to new participants!", "success")
    return redirect(url_for("trip.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/cancel", methods=["POST"])
@flask_login.login_required
def cancel_proposal(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user
    if current_user not in proposal.editors:
        abort(403)

    proposal.status = ProposalStatus.cancelled
    db.session.commit()

    flash("Trip proposal has been cancelled!", "success")
    return redirect(url_for("trip.detail", trip_id=trip_id))

@bp.route("/<int:trip_id>/reopen", methods=["POST"])
@flask_login.login_required
def reopen_proposal(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in proposal.editors:
        abort(403)

    proposal.status = ProposalStatus.open
    proposal.description_final = False
    proposal.destination_final = False
    proposal.budget_final = False
    proposal.departure_locations_final = False
    proposal.activities_final = False
    proposal.start_date_final = False
    proposal.end_date_final = False
    proposal.max_participants_final = False
    db.session.commit()

    flash("Trip proposal has been reopened!", "success")
    return redirect(url_for("trip.detail", trip_id=trip_id))


