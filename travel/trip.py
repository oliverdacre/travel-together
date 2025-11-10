from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
import flask_login
from datetime import datetime
from . import db
from .model import TripProposal, ProposalStatus

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

    flash("Trip proposal created successfully!")
    return redirect(url_for("trip.detail", trip_id=new_proposal.id))


@bp.route("/<int:trip_id>")
@flask_login.login_required
def detail(trip_id):
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)
    return render_template("trip/detail.html", proposal=proposal)


@bp.route("/all")
@flask_login.login_required
def list_all():
    trips = db.session.execute(db.select(TripProposal)).scalars().all()
    return render_template("trip/list.html", trips=trips)
