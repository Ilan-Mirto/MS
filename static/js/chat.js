const socket = io();
const connection = document.getElementById('connection');
const connectionLabel = document.getElementById('connection-label');
const messages = document.getElementById('messages');
const imageInput = document.getElementById('image-input');
const emptyState = document.getElementById('empty-state');
const form = document.getElementById('message-form');
const displayName = document.getElementById('display-name');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const sendImgButton = document.getElementById('send-img-button');

// Restaure le nom saisi précédemment et le sauvegarde à chaque modification.
displayName.value = localStorage.getItem('chat-display-name') || '';
displayName.addEventListener('input', () => {
  localStorage.setItem('chat-display-name', displayName.value.trim());
});

// Met à jour l'indicateur et autorise l'envoi quand le serveur est joignable.
socket.on('connect', () => {
  connection.classList.add('connected');
  connectionLabel.textContent = 'Connecté';
  sendButton.disabled = false;
});

// Signale la perte de connexion et empêche l'envoi tant qu'elle dure.
socket.on('disconnect', () => {
  connection.classList.remove('connected');
  connectionLabel.textContent = 'Déconnecté';
  sendButton.disabled = true;
});

// Affiche chaque message reçu du serveur dans la liste de discussion.
socket.on('chat_message', (message) => {
  emptyState.remove();

  const item = document.createElement('li');
  item.className = 'message';
  // La classe « own » permet de distinguer visuellement ses propres messages.
  item.classList.toggle('own', message.sender_id === socket.id);

  const metadata = document.createElement('div');
  metadata.className = 'message-meta';
  const author = document.createElement('strong');
  author.textContent = message.name;
  const time = document.createElement('time');
  time.dateTime = message.timestamp;
  time.textContent = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });
  metadata.append(author, time);

  const text = document.createElement('p');
  // textContent affiche le texte sans interpréter d'éventuelles balises HTML.
  text.textContent = message.text;
  item.append(metadata, text);
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
});

// Intercepte l'envoi du formulaire pour transmettre le message via Socket.IO.
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  // Ignore les messages vides et attend le retour de la connexion si nécessaire.
  if (!text || !socket.connected) return;

  // Utilise « Anonyme » si aucun nom n'a été saisi.
  socket.emit('send_message', {
    name: displayName.value.trim() || 'Anonyme',
    text
  });
  messageInput.value = '';
  messageInput.focus();
});

// Intercepte le clic sur le bouton d'envoi d'image pour transmettre l'image via Socket.IO.
sendImgButton.addEventListener('click', () => {
  const imageUrl = prompt('Entrez l\'URL de l\'image :');
  if (!imageUrl || !socket.connected) return;

  socket.emit('send_image', {
    name: displayName.value.trim() || 'Anonyme',
    image_url: imageUrl.trim()
  });
});

// Affiche chaque image reçue du serveur dans la liste de discussion.
socket.on('chat_image', (message) => {
  emptyState.remove();

  const item = document.createElement('li');
  item.className = 'message';
  item.classList.toggle('own', message.sender_id === socket.id);

  const metadata = document.createElement('div');
  metadata.className = 'message-meta';
  const author = document.createElement('strong');
  author.textContent = message.name;
  const time = document.createElement('time');
  time.dateTime = message.timestamp;
  time.textContent = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });
  metadata.append(author, time);

  const image = document.createElement('img');
  image.src = message.image_url;
  image.alt = 'Image partagée';
  image.style.maxWidth = '100px';
  image.style.height = 'auto';
  item.append(metadata, image);
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
});