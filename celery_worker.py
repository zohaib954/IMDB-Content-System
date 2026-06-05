from app import create_app
from app.extensions import celery, init_celery

app = create_app()
init_celery(app)

with app.app_context():
    from app.movies import tasks  # noqa: F401