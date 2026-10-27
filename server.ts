import express, { Request, Response } from 'express';
import { spawn } from 'child_process';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = 3000;
const FLASK_PORT = 5001;

// Inicializa o processo Python com Flask
console.log(`Iniciando backend Python Flask na porta interna ${FLASK_PORT}...`);
const pythonProcess = spawn('python3', ['run.py', '--port', String(FLASK_PORT), '--host', '127.0.0.1'], {
  stdio: 'inherit',
  env: {
    ...process.env,
    PYTHONUNBUFFERED: '1',
    PATH: `${process.env.PATH}:/root/.local/bin`
  }
});

pythonProcess.on('error', (err) => {
  console.error('Erro ao iniciar o processo Python:', err);
});

pythonProcess.on('exit', (code, signal) => {
  console.log(`Processo Python finalizado (código: ${code}, sinal: ${signal})`);
});

// Garante limpeza ao finalizar
process.on('exit', () => pythonProcess.kill());
process.on('SIGINT', () => { pythonProcess.kill(); process.exit(); });
process.on('SIGTERM', () => { pythonProcess.kill(); process.exit(); });

// Configura o proxy reverso para encaminhar todo o tráfego HTTP para o Flask
const flaskProxy = createProxyMiddleware({
  target: `http://127.0.0.1:${FLASK_PORT}`,
  changeOrigin: true,
  ws: true,
  on: {
    error: (_err: Error, _req: Request, res: any) => {
      if (res && !res.headersSent && typeof res.writeHead === 'function') {
        res.writeHead(503, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(`
          <!DOCTYPE html>
          <html lang="pt-BR">
            <head>
              <meta charset="UTF-8">
              <meta http-equiv="refresh" content="2">
              <title>Iniciando LogiFleet...</title>
              <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body class="d-flex align-items-center justify-content-center vh-100 bg-light text-center">
              <div class="card p-4 shadow-sm border-0" style="max-width: 420px;">
                <div class="spinner-border text-primary mx-auto mb-3" style="width: 3rem; height: 3rem;" role="status"></div>
                <h5 class="fw-bold text-dark">Inicializando Servidor LogiFleet</h5>
                <p class="text-secondary small mb-0">Carregando serviços Python Flask, banco relacional SQLite e rotas operacionais...</p>
              </div>
            </body>
          </html>
        `);
      }
    }
  }
});

app.use(flaskProxy);

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Servidor HTTP pronto e escutando em http://0.0.0.0:${PORT}`);
});
