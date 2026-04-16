from flask import Flask
from .extensions import init_extensions, db, scheduler


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Basic config; can be overridden by instance/config.py or environment
    app.config.from_mapping(
        SECRET_KEY="dev",  # replace in production
        DATABASE="sqlite:///parking.db",
        SCHEDULER_ENABLED=True,
    )

    # Load default config object if exists
    try:
        from . import default_settings  # noqa: F401
        app.config.from_object("app.default_settings")
    except Exception:
        pass

    # Load instance config, if present
    app.config.from_pyfile("config.py", silent=True)

    # Initialize extensions (db, login, mail, scheduler)
    init_extensions(app)

    # Register blueprints
    from .blueprints.auth import bp as auth_bp
    from .blueprints.parking import bp as parking_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.owner import bp as owner_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parking_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(owner_bp)

    # Create tables and seed defaults on first run
    with app.app_context():
        from .models import create_default_data  # noqa: WPS433
        db.create_all()
        create_default_data()

        # Register scheduler job to release expired bookings
        from .jobs import release_expired_bookings  # noqa: WPS433
        if app.config.get("SCHEDULER_ENABLED", True):
            try:
                scheduler.add_job(
                    release_expired_bookings,
                    id="release_expired_bookings",
                    trigger="interval",
                    minutes=1,
                    replace_existing=True,
                )
            except Exception:
                pass

    @app.route("/health")
    def healthcheck():
        return {"status": "ok"}

    return app


