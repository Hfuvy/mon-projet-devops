from flask import Flask, render_template
import os
import psycopg2

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'monappdb'),
        user=os.environ.get('DB_USER', 'admin'),
        password=os.environ.get('DB_PASS', 'secret')
    )
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS visites (
            id SERIAL PRIMARY KEY,
            compteur INTEGER DEFAULT 0
        );
    ''')
    cur.execute("INSERT INTO visites (id, compteur) SELECT 1, 0 WHERE NOT EXISTS (SELECT 1 FROM visites);")
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def hello():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE visites SET compteur = compteur + 1 WHERE id = 1 RETURNING compteur;")
    compteur = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    env = os.environ.get('ENV', 'local')
    return render_template('index.html', compteur=compteur, env=env)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)