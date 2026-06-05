from flask_pymongo import PyMongo
from celery import Celery

mongo = PyMongo()
celery = Celery()


def init_celery(app):
    """Bind Celery to Flask app context so tasks can use app.config."""
    celery.config_from_object({
        "broker_url": app.config["CELERY_BROKER_URL"],
        "result_backend": app.config["CELERY_RESULT_BACKEND"],
        "task_serializer": "json",
        "accept_content": ["json"],
    })

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery