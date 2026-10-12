# Salon général

Application web de discussion publique en temps réel, construite avec Flask et Flask-SocketIO. Les visiteurs peuvent choisir un nom, envoyer des messages texte ou partager une image par URL, et voir les contributions des autres personnes connectées au salon.

## Fonctionnalités

- Interface de chat en français, avec indicateur de connexion.
- Diffusion en temps réel des messages à tous les clients connectés.
- Partage d’images à partir d’une URL, via le bouton « Envoyer une image ».
- Nom d’affichage mémorisé dans le navigateur.
- Limites côté serveur : nom limité à 24 caractères, message texte et URL d’image à 500 caractères.

Les messages ne sont pas enregistrés : ils ne sont visibles que par les personnes connectées au moment de leur envoi et disparaissent lorsque la page est rechargée ou que le serveur redémarre. Les images ne sont pas téléversées ni stockées par l’application ; les navigateurs chargent l’image depuis l’URL fournie. Le salon est public et ne nécessite pas de compte.

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

Les tests vérifient notamment le chargement de la page et des ressources statiques, la connexion Socket.IO et la diffusion des messages texte entre clients.

## Déploiement sur Render

Le fichier `render.yaml` décrit le service web Render. Il installe les dépendances avec `pip install -r requirements.txt` et démarre l’application avec :

```bash
gunicorn --bind 0.0.0.0:$PORT --worker-class gthread --workers 1 --threads 100 server:app
```

La configuration utilise un seul worker : les diffusions Socket.IO reposent sur la mémoire du processus et aucun stockage partagé ou système de messages externe n’est configuré.

## Structure du projet

```text
.
├── server.py             # Application Flask et événements Socket.IO
├── templates/
│   └── index.html        # Page du salon
├── static/
│   ├── css/chat.css      # Styles de l’interface
│   └── js/chat.js        # Connexion et interactions du chat
├── test/
│   └── test_server.py    # Tests du serveur
├── requirements.txt      # Dépendances Python
└── render.yaml           # Configuration de déploiement Render
```
