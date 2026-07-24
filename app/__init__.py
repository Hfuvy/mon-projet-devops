from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from prometheus_flask_exporter import PrometheusMetrics  
import os

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
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

    #  NOUVEAU : Activer les métriques Prometheus
    metrics = PrometheusMetrics(app)
    
    # Ajouter des métriques personnalisées (optionnel)
    @metrics.histogram('http_request_duration_seconds', 'Duration of HTTP requests in seconds',
                       labels={'method': lambda: request.method, 'endpoint': lambda: request.path})
    def get_duration():
        return 0  # La durée est mesurée automatiquement

    # Importer les modèles et les routes
    from . import models
    from . import routes
    app.register_blueprint(routes.bp)

    return app