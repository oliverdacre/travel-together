from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
import flask_login
from . import db
from .model import User, Message

bp = Blueprint("main", __name__)

@bp.route("/")
@flask_login.login_required
def index():
    return render_template("main/index.html")

@bp.route("/profile/<int:user_id>")
@flask_login.login_required
def profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return render_template("main/profile.html", user=user)

@bp.route("/profile/edit")
@flask_login.login_required
def edit_profile():
    return render_template("main/edit_profile.html")

@bp.route("/profile/edit", methods=["POST"])
@flask_login.login_required
def edit_profile_post():
    description = request.form.get("description", "").strip()
    
    # Validate description length
    if len(description) > 500:
        flash("Description is too long (maximum 500 characters)")
        return redirect(url_for("main.edit_profile"))
    
    # for the user description
    current_user = flask_login.current_user
    current_user.description = description if description else None
    db.session.commit()
    
    flash("Profile updated successfully!")
    return redirect(url_for("main.profile", user_id=current_user.id))

@bp.route("/trip/<int:trip_id>/message_board")
def message_board(trip_id):
    query = db.select(Message).where(Message.proposal_id == trip_id).order_by(Message.timestamp)
    messages = db.session.execute(query).scalars().all()
    return render_template("main/message_board.html", trip_id=trip_id, messages=messages)

@bp.route("/trip/<int:trip_id>/message_board", methods=["POST"])
def post_message(trip_id):
    message = request.form.get("message")
    new_message = Message(content=message, user_id=1, proposal_id=trip_id)  # Assuming user_id=1 for simplicity
    db.session.add(new_message)
    db.session.commit()
    return redirect( url_for("main.message_board", trip_id=trip_id) )