# On prend une image légère Python
FROM python:3.9-slim

# On définit le répertoire de travail
WORKDIR /app

# On copie les dépendances d'abord (pour profiter du cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# On copie tout le reste du code
COPY . .

# On expose le port
EXPOSE 5000

# On lance l'app
CMD ["python", "app.py"]