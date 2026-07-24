import os
import sys
import pytest
import bcrypt
from app import create_app
from app.models import db as _db
from app.models import User, Task

# Ajouter le chemin du projet (utile en local)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope='function')
def app():
    # ✅ Forcer l'utilisation de SQLite en mémoire pour les tests
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()
        _db.session.remove()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def db(app):
    return _db

@pytest.fixture(scope='function')
def user(db):
    hashed = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt())
    user = User(username='testuser', password_hash=hashed.decode('utf-8'))
    db.session.add(user)
    db.session.commit()
    return user