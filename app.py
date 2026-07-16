from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    # On a changé le message pour marquer la version 2 !
    return f"DevOps en action ! Version 2.0 - Env : {os.environ.get('ENV', 'local')}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)