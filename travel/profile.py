from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
import flask_login
from . import db
from .model import User

bp = Blueprint("profile", __name__, url_prefix="/profile")

@bp.route("/<int:user_id>")
@flask_login.login_required
def profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return render_template("profile/profile.html", user=user)

@bp.route("/edit")
@flask_login.login_required
def edit_profile():
    return render_template("profile/edit_profile.html")

@bp.route("/edit", methods=["POST"])
@flask_login.login_required
def edit_profile_post():
    description = request.form.get("description", "").strip()
    
    # Validate description length
    if len(description) > 500:
        flash("Description is too long (maximum 500 characters)")
        return redirect(url_for("profile.edit_profile"))
    
    # for the user description
    current_user = flask_login.current_user
    current_user.description = description if description else None
    db.session.commit()
    
    flash("Profile updated successfully!")
    return redirect(url_for("profile.profile", user_id=current_user.id))