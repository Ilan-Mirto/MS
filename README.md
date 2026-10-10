# MS

## Serveur Flask avec Socket.IO

Cette application utilise Flask et Flask-SocketIO pour établir une connexion
en temps réel entre le navigateur et le serveur Python.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python server.py
```

Ouvre ensuite [http://localhost:3000](http://localhost:3000). La page indique
si le navigateur est connecté au serveur. Le client Socket.IO du navigateur
est chargé depuis le CDN Socket.IO. Le port peut être changé avec la variable
d'environnement `PORT`.

Pour lancer les tests :

```sh
python -m unittest discover -s test
```
