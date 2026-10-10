const { createServer } = require('node:http');
const { readFile } = require('node:fs/promises');
const path = require('node:path');
const { Server } = require('socket.io');

function createAppServer() {
  const httpServer = createServer(async (request, response) => {
    if (request.url === '/') {
      try {
        const html = await readFile(path.join(__dirname, 'index.html'));
        response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
        response.end(html);
      } catch {
        response.writeHead(500);
        response.end('Unable to load the page');
      }
      return;
    }

    response.writeHead(404);
    response.end('Not found');
  });

  const io = new Server(httpServer);

  io.on('connection', (socket) => {
    console.log(`Client connecté : ${socket.id}`);
    socket.on('disconnect', () => {
      console.log(`Client déconnecté : ${socket.id}`);
    });
  });

  return { httpServer, io };
}

if (require.main === module) {
  const { httpServer } = createAppServer();
  const port = process.env.PORT || 3000;

  httpServer.listen(port, () => {
    console.log(`Serveur disponible sur http://localhost:${port}`);
  });
}

module.exports = { createAppServer };
