from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify, current_app, send_from_directory
import flask_login
from . import db
from .model import ProposalStatus, User, Message, TripProposal, TripProposalParticipation, Image
import os
from werkzeug.utils import secure_filename

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
    
    if proposal.status not in [ProposalStatus.open, ProposalStatus.closed]:
        flash(f"Message board is now read-only as the trip proposal's status is: {proposal.status.value}.")

    query = db.select(Message).where(Message.proposal_id == trip_id).order_by(Message.timestamp)
    messages = db.session.execute(query).scalars().all()
    return render_template("main/message_board.html", trip_id=trip_id, messages=messages, proposal=proposal)

@bp.route("/trip/<int:trip_id>/message_board", methods=["POST"])
@flask_login.login_required
def post_message(trip_id):
    message = request.form.get("message")
    images = request.files.getlist("images")
    
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

    # Check if proposal allows messages (open or closed)
    if proposal.status not in [ProposalStatus.open, ProposalStatus.closed]:
        flash("Cannot post messages - the trip proposal is not open or closed.")
        return redirect(url_for("main.message_board", trip_id=trip_id))

    # Validate description length
    if len(message) > 1000:
        flash("Message is too long (maximum 1000 characters)")
        return redirect(url_for("main.message_board", trip_id=trip_id))

    new_message = Message(content=message, user_id=current_user.id, proposal_id=trip_id)
    db.session.add(new_message)
    db.session.flush()  # Get the message ID without committing

    # Process images
    if images:
        for image in images:
            if image.filename:  # Check if a file was actually uploaded
                # Get file extension from original filename
                original_filename = secure_filename(image.filename)
                file_ext = os.path.splitext(original_filename)[1]
                
                # Create Image record to get the ID
                new_image = Image(file_path='', message_id=new_message.id, proposal_id=trip_id)
                db.session.add(new_image)
                db.session.flush()  # Get the image ID without committing
                
                # Use the image ID as filename
                filename = f"{new_image.id}{file_ext}"
                new_image.file_path = filename
                
                # Save the file with the ID as filename
                image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

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
            'images': [url_for('main.uploaded_file', filename=image.file_path) for image in msg.images],
            'user_name': msg.user.name,
            'user_id': msg.user.id,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in messages
    ]
    
    return jsonify(messages_data)

@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)