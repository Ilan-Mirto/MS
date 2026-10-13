const socket = io();
const connection = document.getElementById('connection');
const connectionLabel = document.getElementById('connection-label');
const messages = document.getElementById('messages');
const form = document.getElementById('message-form');
const currentUserId = Number(messages.dataset.userId);
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const sendImgButton = document.getElementById('send-img-button');

// Met à jour l'indicateur et autorise l'envoi quand le serveur est joignable.
socket.on('connect', () => {
  connection.classList.add('connected');
  connectionLabel.textContent = 'Connecté';
  sendButton.disabled = false;
  sendImgButton.disabled = false;
});

// Signale la perte de connexion et empêche l'envoi tant qu'elle dure.
socket.on('disconnect', () => {
  connection.classList.remove('connected');
  connectionLabel.textContent = 'Déconnecté';
  sendButton.disabled = true;
  sendImgButton.disabled = true;
});

function renderMessage(message) {
  document.getElementById('empty-state')?.remove();
  const item = document.createElement('li');
  item.className = 'message';
  item.classList.toggle('own', Number(message.user_id) === currentUserId);

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

  if (message.text !== undefined) {
    const text = document.createElement('p');
    text.textContent = message.text;
    item.append(metadata, text);
  } else {
    const image = document.createElement('img');
    image.src = message.image_url;
    image.alt = 'Image partagée';
    image.style.maxWidth = '100px';
    image.style.height = 'auto';
    item.append(metadata, image);
  }

  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
}

function renderEmptyState() {
  const item = document.createElement('li');
  item.className = 'empty-state';
  item.id = 'empty-state';
  const title = document.createElement('strong');
  title.textContent = 'Le salon est calme pour le moment.';
  const hint = document.createElement('span');
  hint.textContent = 'Écris le premier message.';
  item.append(title, hint);
  messages.append(item);
}

socket.on('chat_history', (history) => {
  messages.replaceChildren();
  if (!history.length) {
    renderEmptyState();
    return;
  }
  history.forEach(renderMessage);
});

socket.on('chat_message', (message) => {
  renderMessage(message);
});

socket.on('system_message', (message) => {
  document.getElementById('empty-state')?.remove();
  const item = document.createElement('li');
  item.className = 'system-message';
  const text = document.createElement('span');
  text.textContent = message.text;
  const time = document.createElement('time');
  time.dateTime = message.timestamp;
  time.textContent = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });
  item.append(text, time);
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
});

// Intercepte l'envoi du formulaire pour transmettre le message via Socket.IO.
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  // Ignore les messages vides et attend le retour de la connexion si nécessaire.
  if (!text || !socket.connected) return;

  socket.emit('send_message', {
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
    image_url: imageUrl.trim()
  });
});

socket.on('chat_image', (message) => {
  renderMessage(message);
});