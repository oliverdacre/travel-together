from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import flask_login
import secrets

from . import db
from . import model

bp = Blueprint("auth", __name__)

@bp.route("/signup")
def signup():
    return render_template("auth/signup.html")

@bp.route("/signup", methods=["POST"])
def signup_post():
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    password_repeat = request.form.get("password_repeat")

    if password != password_repeat:
        flash("Sorry, passwords are different")
        return redirect(url_for("auth.signup"))

    query = db.select(model.User).where(model.User.email == email)
    user = db.session.execute(query).scalar_one_or_none()
    if user:
        flash("Sorry, the email you provided is already registered")
        return redirect(url_for("auth.signup"))

    # Generate a cryptographically secure salt
    salt = secrets.token_hex(16)
    # Hash the password with the salt
    password_hash = generate_password_hash(password + salt, method='pbkdf2:sha256')
    new_user = model.User(email=email, name=username, password_hash=password_hash, salt=salt)
    db.session.add(new_user)
    db.session.commit()

    flash("You've successfully signed up!")
    return redirect(url_for("auth.login"))

@bp.route("/login")
def login():
    return render_template("auth/login.html")

@bp.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")

    query = db.select(model.User).where(model.User.email == email)
    user = db.session.execute(query).scalar_one_or_none()

    if user and user.salt and check_password_hash(user.password_hash, password + user.salt):
        flask_login.login_user(user)
        return redirect(url_for("main.index"))
    else:
        flash("Wrong email and/or password")
        return redirect(url_for("auth.login"))

@bp.route("/logout")
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for("auth.login"))

