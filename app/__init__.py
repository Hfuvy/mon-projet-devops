from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from prometheus_flask_exporter import PrometheusMetrics
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# ✅ Variable globale pour éviter la duplication des métriques
_custom_metrics_registered = False

def create_app():
    global _custom_metrics_registered
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clef-dev-pas-pour-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://admin:secret@db:5432/monappdb')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Branchement des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # Activer les métriques Prometheus
    metrics = PrometheusMetrics(app)

    # ✅ Métriques personnalisées : enregistrées une seule fois
    if not _custom_metrics_registered:
        @metrics.histogram('http_request_duration_seconds',
                           'Duration of HTTP requests in seconds',
                           labels={'method': lambda: request.method,
                                   'endpoint': lambda: request.path})
        def get_duration():
            return 0  # La durée est mesurée automatiquement
        _custom_metrics_registered = True

    from . import models
    from . import routes
    app.register_blueprint(routes.bp)

    return app