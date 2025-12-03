from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
import flask_login
from datetime import datetime
from . import db
from .model import TripProposal, ProposalStatus, TripProposalParticipation, UserRating, Meetup

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
        budget=budget_value,
        departure_locations=departure_locations if departure_locations else None,
        activities=activities if activities else None,
        start_date=start_date_obj,
        end_date=end_date_obj,
        max_participants=max_participants_int,
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
        new_proposal.status = ProposalStatus.closed
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

    is_participant = participation is not None

    participants = []
    if is_participant:
        participants = (
            db.session.execute(
                db.select(TripProposalParticipation).where(
                    TripProposalParticipation.proposal_id == trip_id
                )
            ).scalars().all()
        )

    meetups = []
    if is_participant:
        meetups = (
            db.session.execute(
                db.select(Meetup).where(
                    Meetup.proposal_id == trip_id
                ).order_by(Meetup.scheduled_time)
            ).scalars().all()
        )

    return render_template(
        "trip/detail.html",
        proposal=proposal,
        participants=participants,
        is_participant=is_participant,
        meetups=meetups,
        current_time=datetime.utcnow(),
    )


@bp.route("/<int:trip_id>/join", methods=["POST"])
@flask_login.login_required
def join_trip(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    if proposal.status != ProposalStatus.open:
        flash("This trip is not open for new participants.")
        return redirect(url_for("trip.detail", trip_id=trip_id))  

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
        proposal.status = ProposalStatus.closed
        db.session.commit()
        flash("This trip is already full.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participation = TripProposalParticipation(user_id=user.id, proposal_id=trip_id)
    db.session.add(participation)
    db.session.commit()

    if len(current_count) + 1 >= proposal.max_participants:
        proposal.status = ProposalStatus.closed
        db.session.commit()

    flash("You have successfully joined the trip!")
    return redirect(url_for("trip.detail", trip_id=trip_id))


@bp.route("/<int:trip_id>/leave", methods=["GET", "POST"])
@flask_login.login_required
def leave_trip(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    user = flask_login.current_user

    participation = db.session.scalar(
        db.select(TripProposalParticipation).where(
            TripProposalParticipation.user_id == user.id,
            TripProposalParticipation.proposal_id == trip_id
        )
    )

    if not participation:
        flash("You are not a participant of this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participants = db.session.scalars(
        db.select(TripProposalParticipation).where(
            TripProposalParticipation.proposal_id == trip_id
        )
    ).all()

    current_count = len(participants)

    # Cannot leave a finalized trip
    if proposal.status == ProposalStatus.finalized:
        flash("You cannot leave a finalized trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    # Only editor cannot leave open or closed trip
    if proposal.status in [ProposalStatus.open, ProposalStatus.closed]:
        if participation.is_editor and len(proposal.editors) == 1 and current_count > 1:
            flash("You are the only editor. Please assign another editor or before leaving.")
            return redirect(url_for("trip.detail", trip_id=trip_id))

    # Delete participation
    db.session.delete(participation)
    new_count = current_count - 1

    # Last person leaves -> delete trip
    if new_count == 0:
        proposal.status = ProposalStatus.deleted
        db.session.commit()
        flash("You left the trip. The trip has been deleted because no participants remain.")
        return redirect(url_for("trip.list_all"))

    # If trip was closed and now falls below max capacity -> reopen
    if proposal.status == ProposalStatus.closed and new_count < proposal.max_participants:
        proposal.status = ProposalStatus.open

    db.session.commit()

    flash("You have successfully left the trip.")
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

    # --- Get form values ---
    description = request.form.get("description", "").strip()
    destination = request.form.get("destination", "").strip()
    budget = request.form.get("budget", "").strip()
    departure_locations = request.form.get("departure_locations", "").strip()
    activities = request.form.get("activities", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()
    max_participants = request.form.get("max_participants", "").strip()

    # --- Get final flags from checkboxes ---
    description_final_form = bool(request.form.get("description_final"))
    destination_final_form = bool(request.form.get("destination_final"))
    budget_final_form = bool(request.form.get("budget_final"))
    departure_locations_final_form = bool(request.form.get("departure_locations_final"))
    activities_final_form = bool(request.form.get("activities_final"))
    start_date_final_form = bool(request.form.get("start_date_final"))
    end_date_final_form = bool(request.form.get("end_date_final"))
    max_participants_final_form = bool(request.form.get("max_participants_final"))

    # --- Validate required fields ---
    if (not (destination or proposal.destination_final)
        or not (start_date or proposal.start_date_final)
        or not (end_date or proposal.end_date_final)
        or not (max_participants or proposal.max_participants_final)):
        flash("Please fill in all required fields (destination, dates, max participants).")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    # --- Parse dates ---
    if not proposal.start_date_final:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid start date format. Use YYYY-MM-DD.")
            return redirect(url_for("trip.edit_trip", trip_id=trip_id))
    else:
        start_date_obj = proposal.start_date

    if not proposal.end_date_final:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid end date format. Use YYYY-MM-DD.")
            return redirect(url_for("trip.edit_trip", trip_id=trip_id))
    else:
        end_date_obj = proposal.end_date

    if end_date_obj < start_date_obj:
        flash("End date must be after start date.")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    # --- Parse max participants ---
    if not proposal.max_participants_final:
        try:
            max_participants_int = int(max_participants)
            if max_participants_int <= 0:
                raise ValueError
        except ValueError:
            flash("Max participants must be a positive number.")
            return redirect(url_for("trip.edit_trip", trip_id=trip_id))
    else:
        max_participants_int = proposal.max_participants

    # --- Check participants count vs max ---
    current_participants_count = len(proposal.participants)
    if max_participants_int < current_participants_count:
        flash(f"Max participants cannot be less than current participants ({current_participants_count}).")
        return redirect(url_for("trip.edit_trip", trip_id=trip_id))

    # --- Parse budget ---
    if not proposal.budget_final:
        try:
            budget_value = float(budget) if budget else None
        except ValueError:
            flash("Invalid budget value.")
            return redirect(url_for("trip.edit_trip", trip_id=trip_id))
    else:
        budget_value = proposal.budget

    # --- Update fields if not final ---
    if not proposal.description_final:
        proposal.description = description if description else None
    if not proposal.destination_final:
        proposal.destination = destination
    if not proposal.budget_final:
        proposal.budget = budget_value
    if not proposal.departure_locations_final:
        proposal.departure_locations = departure_locations if departure_locations else None
    if not proposal.activities_final:
        proposal.activities = activities if activities else None
    if not proposal.start_date_final:
        proposal.start_date = start_date_obj
    if not proposal.end_date_final:
        proposal.end_date = end_date_obj
    if not proposal.max_participants_final:
        proposal.max_participants = max_participants_int

    # --- Update final flags ---
    proposal.description_final = proposal.description_final or description_final_form
    proposal.destination_final = proposal.destination_final or destination_final_form
    proposal.budget_final = proposal.budget_final or budget_final_form
    proposal.departure_locations_final = proposal.departure_locations_final or departure_locations_final_form
    proposal.activities_final = proposal.activities_final or activities_final_form
    proposal.start_date_final = proposal.start_date_final or start_date_final_form
    proposal.end_date_final = proposal.end_date_final or end_date_final_form
    proposal.max_participants_final = proposal.max_participants_final or max_participants_final_form

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

    if proposal.status not in [ProposalStatus.open, ProposalStatus.closed]:
        flash("Cannot modify editors for a trip that is finalized or cancelled.", "danger")
        return redirect(url_for("trip.detail", trip_id=trip_id))

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

@bp.route("/<int:trip_id>/remove_editor", methods=["POST"])
@flask_login.login_required
def remove_editor(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in proposal.editors:
        abort(403)

    if proposal.status not in [ProposalStatus.open, ProposalStatus.closed]:
        flash("Cannot modify editors for a trip that is finalized or cancelled.", "danger")
        return redirect(url_for("trip.detail", trip_id=trip_id))

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
    if not participation.is_editor:
        flash("This user is not an editor.", "warning")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    if participation.user == current_user and len(proposal.editors) == 1:
        flash("You are the only editor. Please assign another editor before removing yourself.", "danger")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    participation.is_editor = False
    db.session.commit()

    flash("User's editor permissions have been revoked!", "success")
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


@bp.route("/<int:trip_id>/rate", methods=["GET"])
@flask_login.login_required
def rate_users(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)
    current_user = flask_login.current_user

    if current_user not in [p.user for p in proposal.participants]:
        flash("You must be a participant to rate users.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    now = datetime.utcnow()
    if proposal.end_date > now:
        flash("You can only rate participants after the trip has ended.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    rateable_users = [
        p.user
        for p in proposal.participants
        if p.user.id != flask_login.current_user.id
    ]

    ratings = {
    r.ratee_id: r.rating
    for r in UserRating.query.filter_by(trip_id=trip_id, rater_id=current_user.id).all()
}

    return render_template(
        "trip/rating.html",
        proposal=proposal,
        users=rateable_users,
        ratings=ratings
    )


@bp.route("/<int:trip_id>/rate", methods=["POST"])
@flask_login.login_required
def submit_ratings(trip_id):
    proposal = TripProposal.query.get_or_404(trip_id)

    current_user = flask_login.current_user

    participant_ids = [p.user.id for p in proposal.participants]
    if current_user.id not in participant_ids:
        flash("You must be a participant to rate others.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    now = datetime.utcnow()
    if proposal.end_date > now:
        flash("You can rate participants only after the trip has ended.")
        return redirect(url_for("trip.detail", trip_id=trip_id))

    for key, value in request.form.items():
        if not key.startswith("rating_"):
            continue

        ratee_id = int(key.replace("rating_", ""))
        rating_value = int(value)

        if ratee_id == current_user.id:
            continue

        if rating_value < 1 or rating_value > 5:
            flash("Invalid rating value.")
            return redirect(url_for("trip.rate_users", trip_id=trip_id))

        existing = UserRating.query.filter_by(
            trip_id=trip_id,
            rater_id=current_user.id,
            ratee_id=ratee_id
        ).first()

        if existing:
            existing.rating = rating_value
        else:
            new_rating = UserRating(
                trip_id=trip_id,
                rater_id=current_user.id,
                ratee_id=ratee_id,
                rating=rating_value
            )
            db.session.add(new_rating)

    db.session.commit()
    flash("Your ratings have been submitted!")
    return redirect(url_for("trip.detail", trip_id=trip_id))


@bp.route("/<int:trip_id>/meetup/new", methods=["GET"])
@flask_login.login_required
def new_meetup(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)
    
    current_user = flask_login.current_user
    
    # editors can create meetups
    if current_user not in proposal.editors:
        flash("You do not have permission to create meetups for this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))
    
    return render_template("trip/new_meetup.html", proposal=proposal)


@bp.route("/<int:trip_id>/meetup/new", methods=["POST"])
@flask_login.login_required
def new_meetup_post(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)
    
    current_user = flask_login.current_user
    
    # editors can create meetups
    if current_user not in proposal.editors:
        flash("You do not have permission to create meetups for this trip.")
        return redirect(url_for("trip.detail", trip_id=trip_id))
    
    location = request.form.get("location", "").strip()
    scheduled_time_str = request.form.get("scheduled_time", "").strip()
    scheduled_date = request.form.get("scheduled_date", "").strip()
    
    if not location:
        flash("Please provide a location for the meetup.")
        return redirect(url_for("trip.new_meetup", trip_id=trip_id))
    
    if not scheduled_date or not scheduled_time_str:
        flash("Please provide both date and time for the meetup.")
        return redirect(url_for("trip.new_meetup", trip_id=trip_id))
    
    try:
        datetime_str = f"{scheduled_date} {scheduled_time_str}"
        scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        flash("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
        return redirect(url_for("trip.new_meetup", trip_id=trip_id))
    
    if len(location) > 200:
        flash("Location is too long (maximum 200 characters)")
        return redirect(url_for("trip.new_meetup", trip_id=trip_id))
    
    new_meetup = Meetup(
        proposal_id=trip_id,
        creator_id=current_user.id,
        location=location,
        scheduled_time=scheduled_time
    )
    
    db.session.add(new_meetup)
    db.session.commit()
    
    flash("Meetup created successfully!")
    return redirect(url_for("trip.detail", trip_id=trip_id))


