"""QueueLess application factory."""

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from app.extensions import csrf, db, login_manager, mail, migrate
from app.models import Role, User
from config import CONFIGS, INSTANCE_DIR


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure the Flask app.

    config_name is "development", "testing", or "production".
    When it is omitted, FLASK_CONFIG is used, then "development".
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS[config_name])
    app.config["CONFIG_NAME"] = config_name

    if config_name == "production" and app.config["SECRET_KEY"] == "dev-change-me":
        raise RuntimeError("Set SECRET_KEY in the environment before production use.")

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    Path(app.static_folder, "uploads").mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Importing models registers them on db.metadata for migrations.
    from app import models  # noqa: F401
    from app.admin import admin_bp
    from app.api import api_bp
    from app.auth import auth_bp
    from app.main import main_bp
    from app.orders import orders_bp
    from app.owner import owner_bp
    from app.payments import payments_bp
    from app.student import student_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(api_bp)
    # The React app sends JSON on the same site through the Vite proxy.
    # Cookie sessions replace the HTML form token on these routes.
    csrf.exempt(api_bp)
    _register_commands(app)
    _register_error_handlers(app)
    return app


def _register_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    def create_admin():
        """Create the local super admin. This command refuses to run in production."""
        if app.config.get("CONFIG_NAME") == "production":
            raise SystemExit("create-admin is for local development only.")
        # Development password, also written in the README. Do not use it in production.
        email = "admin@example.local"
        password = "Campus@123"
        if User.query.filter_by(email=email).first():
            print(f"Admin already exists: {email}")
            return
        admin = User(name="Super Admin", email=email, role=Role.ADMIN, email_verified=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin {email}")


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not allowed"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        # A refresh on a React route such as /orders has no Flask page. Send the app shell.
        index = Path(app.root_path).parent / "frontend" / "dist" / "index.html"
        if request.method == "GET" and index.is_file():
            return send_from_directory(index.parent, "index.html")
        return render_template("errors/404.html"), 404

    assets = Path(app.root_path).parent / "frontend" / "dist" / "assets"

    @app.route("/assets/<path:filename>")
    def react_assets(filename: str):
        return send_from_directory(assets, filename)

    @app.errorhandler(500)
    def server_error(error):
        # Log the real exception. The page shown to the user stays generic.
        app.logger.exception("Unhandled server error: %s", error)
        return render_template("errors/500.html"), 500
