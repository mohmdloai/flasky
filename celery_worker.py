from app import create_app
from app.celery_app import celery
from app import db

flask_app = create_app()
celery.conf.update(flask_app.config)

class ContextTask(celery.Task):
    """Make celery tasks work with Flask app context"""
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)

celery.Task = ContextTask