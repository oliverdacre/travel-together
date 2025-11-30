from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
import flask_login
from . import db
from .model import User
import os
from werkzeug.utils import secure_filename
import datetime

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
    current_user = flask_login.current_user
    
    # Get form data
    description = request.form.get("description", "").strip()
    gender = request.form.get("gender", "").strip()
    birthday_str = request.form.get("birthday", "").strip()
    location = request.form.get("location", "").strip()
    phone = request.form.get("phone", "").strip()
    profile_photo_file = request.files.get("profile_photo")
    
    # Validate description length
    if len(description) > 500:
        flash("Description is too long (maximum 500 characters)")
        return redirect(url_for("profile.edit_profile"))
    
    # Validate location length
    if len(location) > 100:
        flash("Location is too long (maximum 100 characters)")
        return redirect(url_for("profile.edit_profile"))
    
    # Validate phone length
    if len(phone) > 20:
        flash("Phone number is too long (maximum 20 characters)")
        return redirect(url_for("profile.edit_profile"))
    
    # Process birthday
    birthday = None
    if birthday_str:
        try:
            birthday = datetime.datetime.strptime(birthday_str, "%Y-%m-%d")
            # Validate that birthday is not in the future
            if birthday > datetime.datetime.now():
                flash("Birthday cannot be in the future")
                return redirect(url_for("profile.edit_profile"))
        except ValueError:
            flash("Invalid date format for birthday")
            return redirect(url_for("profile.edit_profile"))
    
    # Process profile photo upload
    if profile_photo_file and profile_photo_file.filename:
        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        original_filename = secure_filename(profile_photo_file.filename)
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            flash("Invalid file type. Please upload an image (JPG, PNG, GIF, or WEBP)")
            return redirect(url_for("profile.edit_profile"))
        
        # Delete old profile photo if it exists
        if current_user.profile_photo:
            old_photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.profile_photo)
            if os.path.exists(old_photo_path):
                try:
                    os.remove(old_photo_path)
                except OSError:
                    pass  # Ignore errors when deleting old file
        
        # Generate new filename using user ID
        new_filename = f"profile_{current_user.id}{file_ext}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
        
        # Save the file
        profile_photo_file.save(file_path)
        current_user.profile_photo = new_filename
    
    # Update user fields
    current_user.description = description if description else None
    current_user.gender = gender if gender else None
    current_user.birthday = birthday
    current_user.location = location if location else None
    current_user.phone = phone if phone else None
    
    # Calculate and update age from birthday if available
    if birthday:
        today = datetime.date.today()
        birth_date = birthday.date() if isinstance(birthday, datetime.datetime) else birthday
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        current_user.age = age
    
    db.session.commit()
    
    flash("Profile updated successfully!")
    return redirect(url_for("profile.profile", user_id=current_user.id))