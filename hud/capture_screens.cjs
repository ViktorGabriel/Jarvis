const { app, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

const screenshotsDir = path.resolve(__dirname, '../assets/screenshots');
if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    show: true,
    frame: false,
    transparent: false,
    backgroundColor: '#050811',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'electron/preload.cjs'),
    },
  });

  const indexPath = path.resolve(__dirname, 'dist/index.html');
  await win.loadFile(indexPath);

  console.log('[Capture] Aguardando conexão do HUD com o Core Daemon e renderização do Three.js...');
  // Aguarda 4 segundos para o WebSocket conectar e o Three.js AgentOrb animar
  await new Promise((r) => setTimeout(r, 4000));

  // 1. Captura da tela principal ativa com o Orb e Telemetria
  const hudImage = await win.webContents.capturePage();
  const hudPath = path.join(screenshotsDir, 'hud-preview.png');
  fs.writeFileSync(hudPath, hudImage.toPNG());
  console.log(`[Capture] Imagem 1 salva com sucesso: ${hudPath}`);

  // 2. Captura da coluna de telemetria em close-up
  const telemetryImage = await win.webContents.capturePage({
    x: 0,
    y: 40,
    width: 380,
    height: 760,
  });
  const telemetryPath = path.join(screenshotsDir, 'telemetry-preview.png');
  fs.writeFileSync(telemetryPath, telemetryImage.toPNG());
  console.log(`[Capture] Imagem 2 (Telemetria) salva com sucesso: ${telemetryPath}`);

  // 3. Simula uma requisição de aprovação de governança via injeção para capturar o modal de segurança
  console.log('[Capture] Injetando solicitação de governança para capturar modal crítico...');
  await win.webContents.executeJavaScript(`
    (() => {
      // Dispara evento mock no websocket ou renderiza modal
      const fakeApproval = {
        ticket_id: "SEC-8824",
        action_type: "git_push_safe",
        description: "Publicação de código crítico no branch remoto main",
        command: "git push origin main --force-with-lease",
        risk_reason: "Comando com flags de alteração remota não supervisionada. Exige confirmação explícita no HUD."
      };
      // Se existir o evento no app
      window.dispatchEvent(new CustomEvent('jarvis-test-approval', { detail: fakeApproval }));
    })();
  `).catch((e) => console.log('Mock JS error:', e));

  // Aguarda 1 segundo e captura governance preview
  await new Promise((r) => setTimeout(r, 1500));
  const govImage = await win.webContents.capturePage();
  const govPath = path.join(screenshotsDir, 'governance-preview.png');
  fs.writeFileSync(govPath, govImage.toPNG());
  console.log(`[Capture] Imagem 3 (Governança) salva com sucesso: ${govPath}`);

  console.log('[Capture] Todas as capturas foram concluídas!');
  app.quit();
});
