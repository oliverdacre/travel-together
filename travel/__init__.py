from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app(test_config=None):
    app = Flask(__name__)

    # A secret for signing session cookies
    app.config["SECRET_KEY"] = "93220d9b340cf9a6c39bac99cce7daf220167498f91fa"
    
    # replace with real connection string
    # app.config[
    #     "SQLALCHEMY_DATABASE_URI"
    # ] = "mysql+pymysql://26_webapp_XX:YYYYYYYYY@mysql.lab.it.uc3m.es/26_webapp_XXa"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
    db.init_app(app)

    # Register blueprints
    # (we import main from here to avoid circular imports in the next lab)
    from . import main

    app.register_blueprint(main.bp)
    return app