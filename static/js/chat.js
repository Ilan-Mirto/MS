const socket = io();
const connection = document.getElementById('connection');
const connectionLabel = document.getElementById('connection-label');
const messages = document.getElementById('messages');
const emptyState = document.getElementById('empty-state');
const form = document.getElementById('message-form');
const displayName = document.getElementById('display-name');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');

displayName.value = localStorage.getItem('chat-display-name') || '';
displayName.addEventListener('input', () => {
  localStorage.setItem('chat-display-name', displayName.value.trim());
});

socket.on('connect', () => {
  connection.classList.add('connected');
  connectionLabel.textContent = 'Connecté';
  sendButton.disabled = false;
});

socket.on('disconnect', () => {
  connection.classList.remove('connected');
  connectionLabel.textContent = 'Déconnecté';
  sendButton.disabled = true;
});

socket.on('chat_message', (message) => {
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

  const text = document.createElement('p');
  text.textContent = message.text;
  item.append(metadata, text);
  messages.append(item);
  messages.scrollTop = messages.scrollHeight;
});

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !socket.connected) return;

  socket.emit('send_message', {
    name: displayName.value.trim() || 'Anonyme',
    text
  });
  messageInput.value = '';
  messageInput.focus();
});