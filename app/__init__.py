import os
from flask import Flask
from app.config import config_map
from app.extensions import mongo, init_celery
from app.movies.repository import MovieRepository


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    env = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_map[env])

    # Initialize extensions
    mongo.init_app(app)
    init_celery(app)

    # Register blueprints
    from app.movies.routes import movies_bp
    app.register_blueprint(movies_bp)

    # Ensure MongoDB indexes on startup
    with app.app_context():
        try:
            repo = MovieRepository(mongo.db["movies"])
            repo.ensure_indexes()
        except Exception:
            pass  # Don't crash if Atlas unreachable at startup

    @app.errorhandler(413)
    def request_entity_too_large(error):
        from app.core.responses import error_response
        return error_response("File exceeds 1GB limit.", 413)

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app