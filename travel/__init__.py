from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
import os

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # >>> Choose ONE URI — lab MariaDB or local SQLite <<<
    # app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://26_webapp_XX:YYYYYYYYY@mysql.lab.it.uc3m.es/26_webapp_XXa"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"

    db.init_app(app)

    # Flask-Login setup
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    from . import model
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(model.User, int(user_id))

    # Register blueprints
    from . import main
    app.register_blueprint(main.bp)

    from . import auth
    app.register_blueprint(auth.bp)

    # Add template filter for user profile links
    @app.template_filter('user_link')
    def user_link_filter(user):
        """Create a link to a user's profile. Use in templates: {{ user|user_link|safe }}"""
        if user:
            from flask import url_for
            from markupsafe import Markup
            link = f'<a href="{url_for("main.profile", user_id=user.id)}">{user.name}</a>'
            return Markup(link)
        return Markup('')

    return app
