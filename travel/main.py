from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import flask_login

from . import db
from . import model

bp = Blueprint("main", __name__)

@bp.route("/")
@flask_login.login_required
def index():
    return render_template("main/index.html")

@bp.route("/profile/<int:user_id>")
@flask_login.login_required
def profile(user_id):
    user = db.session.get(model.User, user_id)
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