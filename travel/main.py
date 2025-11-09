from flask import Blueprint, redirect, render_template, request, url_for
from . import db
from .model import Message

bp = Blueprint("main", __name__)
@bp.route("/")
def index():
    return render_template("main/index.html")

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