#!/bin/sh

echo "🔄 Application du schéma de base de données (migrations)..."
flask db upgrade

echo "🚀 Lancement de l'application..."
exec python app.py
