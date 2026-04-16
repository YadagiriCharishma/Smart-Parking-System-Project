from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
scheduler = BackgroundScheduler(daemon=True)


def init_extensions(app):
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", "sqlite:///parking.db")
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    mail.init_app(app)

    # Start scheduler if enabled
    if app.config.get("SCHEDULER_ENABLED", True):
        if not scheduler.running:
            scheduler.start()
        # Placeholder job to be replaced when booking release is implemented
        def noop_job():
            return True
        try:
            scheduler.add_job(noop_job, IntervalTrigger(minutes=10), id="heartbeat", replace_existing=True)
        except Exception:
            pass


