from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User, Task
import bcrypt

bp = Blueprint('main', __name__)

# ----- Page d'accueil (publique) -----
@bp.route('/')
def index():
    return render_template('index.html', compteur=0, env="STRUCTURED")

# ----- Inscription -----
@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return redirect(url_for('main.signup'))
        
        # Hacher le mot de passe
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Créer l'utilisateur
        new_user = User(username=username, password_hash=hashed.decode('utf-8'))
        db.session.add(new_user)
        db.session.commit()
        
        flash('Compte créé ! Connectez-vous.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('signup.html')

# ----- Connexion -----
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # Vérifier le mot de passe
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    
    return render_template('login.html')

# ----- Déconnexion -----
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('main.index'))

# ----- Tableau de bord (protégé) -----
@bp.route('/dashboard')
@login_required
def dashboard():
    # Récupérer les tâches de l'utilisateur connecté
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', tasks=tasks)

# ----- Ajouter une tâche -----
@bp.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    description = request.form.get('description')
    
    if title:
        new_task = Task(title=title, description=description, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        flash('Tâche ajoutée !', 'success')
    
    return redirect(url_for('main.dashboard'))

# ----- Supprimer une tâche -----
@bp.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Vérifier que la tâche appartient bien à l'utilisateur connecté
    if task.user_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    db.session.delete(task)
    db.session.commit()
    flash('Tâche supprimée.', 'info')
    return redirect(url_for('main.dashboard'))

# ----- Santé (pour le debug) -----
@bp.route('/health')
def health():
    return "✅ Nouvelle architecture chargée avec authentification !"
