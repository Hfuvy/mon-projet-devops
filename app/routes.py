from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User, Task, Project, Column
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import bcrypt
import re
import csv
from io import StringIO

bp = Blueprint('main', __name__)

# ==============================================
#  PARTIE 1 : AUTHENTIFICATION
# ==============================================

@bp.route('/')
def index():
    return render_template('index.html', compteur=0, env="STRUCTURED")

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if len(password) < 8:
            flash('Le mot de passe doit faire au moins 8 caractères.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[A-Z]', password):
            flash('Le mot de passe doit contenir une majuscule.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[a-z]', password):
            flash('Le mot de passe doit contenir une minuscule.', 'danger')
            return redirect(url_for('main.signup'))
        if not re.search(r'[0-9]', password):
            flash('Le mot de passe doit contenir un chiffre.', 'danger')
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

# ==============================================
#  PARTIE 2 : DASHBOARD (TÂCHES)
# ==============================================

@bp.route('/dashboard')
@login_required
def dashboard():
    query = Task.query.filter_by(user_id=current_user.id)
    filter_status = request.args.get('filter', 'all')
    if filter_status == 'done':
        query = query.filter_by(done=True)
    elif filter_status == 'pending':
        query = query.filter_by(done=False)
    search = request.args.get('q', '')
    if search:
        query = query.filter(Task.title.ilike(f'%{search}%'))
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.order_by(Task.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    tasks = pagination.items
    return render_template('dashboard.html', tasks=tasks, pagination=pagination, filter_status=filter_status, search=search)

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
#  PARTIE 3 : STATISTIQUES (Page + API)
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
    projects_count = Project.query.filter_by(owner_id=current_user.id).count()
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
        'projects': projects_count,
        'labels': date_labels,
        'counts': counts
    })

# ==============================================
#  PARTIE 4 : API REST (JSON)
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
#  PARTIE 5 : EXPORT CSV
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
#  PARTIE 6 : GESTION DES PROJETS (BOARD)
# ==============================================

@bp.route('/projects')
@login_required
def list_projects():
    projects = Project.query.filter_by(owner_id=current_user.id).all()
    return render_template('projects.html', projects=projects)

@bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        if not title:
            flash('Le titre est obligatoire.', 'danger')
            return redirect(url_for('main.create_project'))
        project = Project(title=title, description=description, owner_id=current_user.id)
        db.session.add(project)
        db.session.commit()
        default_columns = ['À faire', 'En cours', 'Terminé']
        for i, col_title in enumerate(default_columns):
            column = Column(title=col_title, order=i, project_id=project.id)
            db.session.add(column)
        db.session.commit()
        flash('Projet créé avec succès !', 'success')
        return redirect(url_for('main.board', project_id=project.id))
    return render_template('create_project.html')

@bp.route('/board/<int:project_id>')
@login_required
def board(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.list_projects'))
    columns = Column.query.filter_by(project_id=project.id).order_by(Column.order).all()
    return render_template('board.html', project=project, columns=columns)

@bp.route('/board/<int:project_id>/add_task', methods=['POST'])
@login_required
def add_task_to_board(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    title = request.form.get('title')
    column_id = request.form.get('column_id')
    if not title or not column_id:
        flash('Titre et colonne obligatoires.', 'danger')
        return redirect(url_for('main.board', project_id=project_id))
    task = Task(
        title=title,
        user_id=current_user.id,
        project_id=project_id,
        column_id=column_id,
        done=False
    )
    db.session.add(task)
    db.session.commit()
    flash('Tâche ajoutée !', 'success')
    return redirect(url_for('main.board', project_id=project_id))

@bp.route('/board/<int:project_id>/add_column', methods=['POST'])
@login_required
def add_column(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    title = request.form.get('title')
    if title:
        max_order = db.session.query(func.max(Column.order)).filter_by(project_id=project_id).scalar() or -1
        column = Column(title=title, order=max_order + 1, project_id=project_id)
        db.session.add(column)
        db.session.commit()
        flash('Colonne ajoutée !', 'success')
    else:
        flash('Le titre de la colonne est obligatoire.', 'danger')
    return redirect(url_for('main.board', project_id=project_id))

@bp.route('/board/<int:project_id>/delete_task/<int:task_id>')
@login_required
def delete_task_from_board(project_id, task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('Action non autorisée.', 'danger')
        return redirect(url_for('main.board', project_id=project_id))
    db.session.delete(task)
    db.session.commit()
    flash('Tâche supprimée.', 'info')
    return redirect(url_for('main.board', project_id=project_id))

@bp.route('/api/board/<int:project_id>/move_task', methods=['POST'])
@login_required
def move_task(project_id):
    data = request.get_json()
    task_id = data.get('task_id')
    new_column_id = data.get('column_id')
    task = Task.query.get_or_404(task_id)
    if task.project_id != project_id or task.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    task.column_id = new_column_id
    db.session.commit()
    return jsonify({'success': True})

# ==============================================
#  PARTIE 7 : UTILITAIRES
# ==============================================

@bp.route('/health')
def health():
    return "✅ Application en ligne !"