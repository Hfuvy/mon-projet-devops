from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User, Task
from sqlalchemy import or_
from datetime import datetime, timedelta
import bcrypt
import re
import csv
from io import StringIO

bp = Blueprint('main', __name__)

# ==============================================
#  PARTIE 1 : PAGES WEB (HTML)
# ==============================================

@bp.route('/')
def index():
    return render_template('index.html', compteur=0, env="STRUCTURED")

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validation du mot de passe
        if len(password) < 8:
            flash('Le mot de passe doit faire au moins 8 caractères.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[A-Z]', password):
            flash('Le mot de passe doit contenir au moins une majuscule.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[a-z]', password):
            flash('Le mot de passe doit contenir au moins une minuscule.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[0-9]', password):
            flash('Le mot de passe doit contenir au moins un chiffre.', 'danger')
            return redirect(url_for('main.signup'))
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return redirect(url_for('main.signup'))
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = User(username=username, password_hash=hashed.decode('utf-8'))
        db.session.add(new_user)
        db.session.commit()
        flash('Compte créé ! Connectez-vous.', 'success')
        return redirect(url_for('main.login'))
    return render_template('signup.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            login_user(user)
            flash('Connexion réussie !', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    query = Task.query.filter_by(user_id=current_user.id)
    
    # Filtre par statut
    filter_status = request.args.get('filter', 'all')
    if filter_status == 'done':
        query = query.filter_by(done=True)
    elif filter_status == 'pending':
        query = query.filter_by(done=False)
    
    # Recherche par titre
    search = request.args.get('q', '')
    if search:
        query = query.filter(Task.title.ilike(f'%{search}%'))
    
    # Pagination (5 par page)
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.order_by(Task.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tasks = pagination.items
    
    return render_template('dashboard.html', 
                         tasks=tasks, 
                         pagination=pagination,
                         filter_status=filter_status, 
                         search=search)

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

@bp.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if title:
            task.title = title
            task.description = description
            db.session.commit()
            flash('Tâche mise à jour !', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Le titre est obligatoire.', 'danger')
    return render_template('edit_task.html', task=task)

@bp.route('/toggle_task/<int:task_id>')
@login_required
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.dashboard'))
    task.done = not task.done
    db.session.commit()
    if task.done:
        flash('Tâche terminée !', 'success')
    else:
        flash('Tâche réouverte.', 'info')
    return redirect(url_for('main.dashboard'))

@bp.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.dashboard'))
    db.session.delete(task)
    db.session.commit()
    flash('Tâche supprimée.', 'info')
    return redirect(url_for('main.dashboard'))

# ==============================================
#  PARTIE 2 : STATISTIQUES (Page + API)
# ==============================================

@bp.route('/stats')
@login_required
def stats():
    return render_template('stats.html')

@bp.route('/api/stats-data')
@login_required
def api_stats_data():
    total = Task.query.filter_by(user_id=current_user.id).count()
    done = Task.query.filter_by(user_id=current_user.id, done=True).count()
    pending = total - done
    
    # Données pour le graphique (7 derniers jours)
    dates = [(datetime.now() - timedelta(days=i)).date() for i in range(6, -1, -1)]
    counts = []
    for d in dates:
        count = Task.query.filter(
            Task.user_id == current_user.id,
            Task.created_at >= d,
            Task.created_at < d + timedelta(days=1)
        ).count()
        counts.append(count)
    
    date_labels = [d.strftime('%d/%m') for d in dates]
    
    return jsonify({
        'total': total,
        'done': done,
        'pending': pending,
        'labels': date_labels,
        'counts': counts
    })

# ==============================================
#  PARTIE 3 : API REST (JSON)
# ==============================================

@bp.route('/api/tasks', methods=['GET'])
@login_required
def api_get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return jsonify([task.to_dict() for task in tasks])

@bp.route('/api/tasks', methods=['POST'])
@login_required
def api_create_task():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'error': 'Le titre est obligatoire'}), 400
    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        user_id=current_user.id
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def api_update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    data = request.get_json()
    if data.get('title') is not None:
        task.title = data['title']
    if data.get('description') is not None:
        task.description = data['description']
    if data.get('done') is not None:
        task.done = bool(data['done'])
    db.session.commit()
    return jsonify(task.to_dict())

@bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Tâche supprimée'}), 200

@bp.route('/api/tasks/<int:task_id>/toggle', methods=['PATCH'])
@login_required
def api_toggle_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    task.done = not task.done
    db.session.commit()
    return jsonify({'id': task.id, 'done': task.done})

# ==============================================
#  PARTIE 4 : EXPORT CSV
# ==============================================

@bp.route('/api/tasks/export', methods=['GET'])
@login_required
def export_tasks_csv():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Titre', 'Description', 'Terminée', 'Date de création'])
    
    for task in tasks:
        writer.writerow([
            task.id,
            task.title,
            task.description or '',
            'Oui' if task.done else 'Non',
            task.created_at.strftime('%d/%m/%Y %H:%M') if task.created_at else ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=tasks_export.csv'}
    )

# ==============================================
#  PARTIE 5 : UTILITAIRES
# ==============================================

@bp.route('/health')
def health():
    return "✅ Application en ligne !"