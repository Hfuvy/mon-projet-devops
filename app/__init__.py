from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clef-dev-pas-pour-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://admin:secret@localhost:5432/monappdb')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Branchement des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'  # On pointe vers la route de login qu'on va créer

    # 🔥 NOUVEAU : On importe les modèles (cela exécute le décorateur @login_manager.user_loader)
    from . import models
    
    # Import et enregistrement des routes
    from . import routes
    app.register_blueprint(routes.bp)

    return app