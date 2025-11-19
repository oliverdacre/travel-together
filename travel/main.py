from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
import flask_login
from . import db
from .model import User, Message, TripProposal, TripProposalParticipation

bp = Blueprint("main", __name__)

@bp.route("/")
@flask_login.login_required
def index():
    return render_template("main/index.html")

@bp.route("/trip/<int:trip_id>/message_board")
@flask_login.login_required
def message_board(trip_id):
    # Ensure the trip exists
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    # Only allow the creator or participants to access the message board
    current_user = flask_login.current_user
    if proposal.creator_id != current_user.id:
        participation = db.session.execute(
            db.select(TripProposalParticipation).where(
                TripProposalParticipation.proposal_id == trip_id,
                TripProposalParticipation.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if participation is None:
            abort(403)

    query = db.select(Message).where(Message.proposal_id == trip_id).order_by(Message.timestamp)
    messages = db.session.execute(query).scalars().all()
    return render_template("main/message_board.html", trip_id=trip_id, messages=messages)

@bp.route("/trip/<int:trip_id>/message_board", methods=["POST"])
@flask_login.login_required
def post_message(trip_id):
    message = request.form.get("message")
    # Ensure the trip exists
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    # Only allow the creator or participants to post
    current_user = flask_login.current_user
    if proposal.creator_id != current_user.id:
        participation = db.session.execute(
            db.select(TripProposalParticipation).where(
                TripProposalParticipation.proposal_id == trip_id,
                TripProposalParticipation.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if participation is None:
            abort(403)

    # Validate description length
    if len(message) > 1000:
        flash("Message is too long (maximum 1000 characters)")
        return redirect(url_for("main.message_board", trip_id=trip_id))

    new_message = Message(content=message, user_id=current_user.id, proposal_id=trip_id)
    db.session.add(new_message)
    db.session.commit()
    return redirect(url_for("main.message_board", trip_id=trip_id))

@bp.route("/trip/<int:trip_id>/messages/since/<int:message_id>")
@flask_login.login_required
def get_messages_since(trip_id, message_id):
    # Ensure the trip exists
    proposal = db.session.get(TripProposal, trip_id)
    if not proposal:
        abort(404)

    # Only allow the creator or participants to access
    current_user = flask_login.current_user
    if proposal.creator_id != current_user.id:
        participation = db.session.execute(
            db.select(TripProposalParticipation).where(
                TripProposalParticipation.proposal_id == trip_id,
                TripProposalParticipation.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if participation is None:
            abort(403)

    # Get messages with ID greater than message_id
    query = db.select(Message).where(
        Message.proposal_id == trip_id,
        Message.id > message_id
    ).order_by(Message.timestamp)
    messages = db.session.execute(query).scalars().all()
    
    # Convert to JSON
    messages_data = [
        {
            'id': msg.id,
            'content': msg.content,
            'user_name': msg.user.name,
            'user_id': msg.user.id,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in messages
    ]
    
    return jsonify(messages_data)