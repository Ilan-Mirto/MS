# Salon général

Application web de discussion publique en temps réel, construite avec Flask et Flask-SocketIO. Les utilisateurs créent leur compte ou se connectent avec leur prénom, leur nom et un mot de passe. Ils peuvent ensuite envoyer des messages texte ou partager une image par URL, et voir les contributions des autres personnes connectées au salon.

## Fonctionnalités

- Interface de chat en français, avec indicateur de connexion.
- Création automatique d'un compte à la première connexion ; reconnexion avec le même prénom, nom et mot de passe. La casse du prénom et du nom n'est pas prise en compte.
- Mots de passe de 8 à 128 caractères, stockés sous forme hachée.
- Session obligatoire pour accéder au salon, à son historique public et aux événements Socket.IO.
- Déconnexion avec invalidation de la session.
- Diffusion en temps réel des messages à tous les clients connectés.
- Historique public des messages texte et des URLs d’images conservé dans une base SQLite et rechargé à la connexion.
- Page d'historique accessible aux utilisateurs connectés à l'adresse `/messages`.
- Partage d’images à partir d’une URL, via le bouton « Envoyer une image ».
- Annonces de connexion discrètes indiquant le nom complet du nouvel utilisateur.
- Limites côté serveur : prénom et nom limités à 40 caractères, message texte et URL d’image à 500 caractères.

Les comptes et messages sont gérés avec SQLAlchemy et enregistrés dans `instance/chat.db` (SQLite) par défaut. Définis `CHAT_DATABASE` pour choisir un autre chemin ou fournir une URL de base de données SQLAlchemy. En déploiement, définis aussi `CHAT_SECRET_KEY` avec une valeur secrète persistante pour conserver les sessions et protéger leur signature. Les images ne sont pas téléversées ni stockées par l’application ; seule leur URL est conservée, et les navigateurs chargent l’image depuis cette adresse. Le salon et son historique restent publics pour les utilisateurs connectés.

## Prérequis

- Python 3.10 ou supérieur
- `pip`

Le navigateur charge la bibliothèque cliente Socket.IO depuis un CDN ; une connexion Internet est donc nécessaire pour utiliser le chat.

## Installation et lancement

Depuis la racine du projet :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```
Sous Windows, active l’environnement virtuel avec `.venv\Scripts\activate`.

Ouvre ensuite [http://localhost:5000](http://localhost:5000). Le serveur écoute sur le port `5000` par défaut ; la variable d’environnement `PORT` permet d’en choisir un autre.

## Tests

```bash
python -m unittest discover -s test -v
```

Les tests vérifient notamment le chargement de la page et des ressources statiques, la connexion Socket.IO, la diffusion des messages et le rechargement de l’historique après reconnexion.

## Déploiement sur Render

Le fichier `render.yaml` décrit le service web Render. Il installe les dépendances avec `pip install -r requirements.txt` et démarre l’application avec :

```bash
gunicorn --bind 0.0.0.0:$PORT --worker-class gthread --workers 1 --threads 100 server:app
```

La configuration utilise un seul worker. Sur Render, le système de fichiers par défaut est éphémère : pour conserver la base après un remplacement ou un redéploiement du service, configure un disque persistant et définis `CHAT_DATABASE` vers un chemin situé sur ce disque.

## Structure du projet

```text
.
├── server.py             # Application Flask et événements Socket.IO
├── models.py             # Modèles SQLAlchemy et extension de base de données
├── views.py              # Routes du salon, de connexion et de l'historique
├── templates/
│   ├── base.html          # Structure HTML commune
│   ├── index.html         # Page du salon
│   ├── login.html         # Création de compte et connexion
│   └── messages.html      # Historique public
├── static/
│   ├── css/chat.css       # Styles de l’interface
│   └── js/chat.js         # Connexion et interactions du chat
├── instance/
│   └── chat.db           # Base SQLite créée au premier lancement
├── test/
│   └── test_server.py    # Tests du serveur
├── requirements.txt      # Dépendances Python
└── render.yaml            # Configuration de déploiement Render
```
