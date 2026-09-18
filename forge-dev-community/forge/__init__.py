from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app() -> Flask:
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config["SECRET_KEY"] = "forge-dev-community-change-me"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{root / 'instance' / 'forge.db'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    (root / "instance").mkdir(exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from forge.models import User
    from forge.routes import auth_bp, main_bp
    from forge.seed import seed_if_empty

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        seed_if_empty()

    return app
