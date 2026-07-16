from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return f" DevOps en action ! Environnement : {os.environ.get('ENV', 'local')}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)