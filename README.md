# MS

## Serveur Flask avec Socket.IO

Cette application utilise Flask et Flask-SocketIO pour discuter en temps réel
entre plusieurs navigateurs. Chaque visiteur choisit un nom et ses messages
sont diffusés aux autres personnes connectées au salon.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Ouvre ensuite [http://localhost:5000](http://localhost:5000). Les messages ne
sont pas enregistrés: ils disparaissent lorsque la page ou le serveur est
redémarré. Le client Socket.IO du navigateur est chargé depuis le CDN Socket.IO.
Le port local peut être changé avec la variable d'environnement `PORT`.

## Accès depuis un autre réseau

La configuration `render.yaml` permet de publier l'application sur Render,
avec une URL accessible depuis Internet et le support des WebSockets.

1. Pousse le projet sur GitHub.
2. Dans Render, choisis **New** puis **Blueprint** et sélectionne le dépôt.
3. Une fois le déploiement terminé, ouvre l'URL `onrender.com` fournie par
	Render depuis les autres appareils.

Le service gratuit peut se mettre en veille après une période sans activité;
la première ouverture peut alors prendre un peu plus de temps. Le site sera
public pour toute personne ayant son URL.

Pour lancer les tests :

```sh
python -m unittest discover -s test
```
