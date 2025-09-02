import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db
from flask_login import LoginManager

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'main.login'  # route name for login

def create_app():
    app = Flask(__name__)  # use name with underscores

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/inventory.db'
    app.config['UPLOAD_FOLDER'] = 'app/static/uploads'

    db.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    login_manager.init_app(app)

    return app