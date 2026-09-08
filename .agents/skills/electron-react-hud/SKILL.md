---
name: electron-react-hud
description: >-
  Guia de desenvolvimento do HUD Electron+React+Three.js do J.A.R.V.I.S: IPC seguro via preload,
  janela frameless/transparente, WebSocket hook com deduplicacao, Three.js WebGL em React,
  Tailwind neon/glassmorphism, hotkeys globais e packaging. Ative ao criar/modificar componentes
  HUD, corrigir problemas de IPC, otimizar Three.js ou estilizar o HUD.
---

# Desenvolvimento do HUD: Electron + React + Three.js

O HUD do J.A.R.V.I.S e uma interface desktop futurista desenvolvida com **Electron 33**, **React 18**, **Vite 5**, **TypeScript**, **Tailwind CSS** e **Three.js**.

---

## 1. Arquitetura de Processos

- **Main Process (`hud/electron/main.cjs`)**: Controla criacao de janelas, atalhos globais do SO e IPC nativo.
  *Nota*: Extensao `.cjs` obrigatoria pois o `package.json` possui `"type": "module"`.
- **Preload Script (`hud/electron/preload.cjs`)**: Ponte segura entre Node.js e o Renderer usando `contextBridge`.
- **Renderer (`hud/src/`)**: SPA React montada via Vite conectada ao daemon Python por WebSocket.

---

## 2. IPC Seguro via Preload

Nunca exponha `ipcRenderer` diretamente na janela global.

### `hud/electron/preload.cjs`
```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvisElectron', {
  minimize: () => ipcRenderer.invoke('window-minimize'),
  toggleMaximize: () => ipcRenderer.invoke('window-toggle-maximize'),
  toggleFullscreen: () => ipcRenderer.invoke('window-toggle-fullscreen'),
  close: () => ipcRenderer.invoke('window-close'),
  togglePin: () => ipcRenderer.invoke('window-toggle-pin'),
});
```

### `hud/electron/main.cjs`
```javascript
ipcMain.handle('window-toggle-fullscreen', () => {
  const isFull = mainWindow.isFullScreen();
  mainWindow.setFullScreen(!isFull);
  return !isFull;
});
```

---

## 3. WebSocket State e Deduplicacao

O hook `useJarvisSocket.ts` gerencia todo o estado reativo compartilhado.

```typescript
// Evita mensagens duplicadas causadas por dev re-renders ou ecos
const messageId = data.id || `${data.timestamp}_${data.content.slice(0, 20)}`;
if (seenIds.current.has(messageId)) return;
seenIds.current.add(messageId);
```

### Regras do React:
- **Sem `<React.StrictMode>`**: StrictMode duplica a montagem do hook de WebSocket em desenvolvimento local.
- **Cleanup no unmount**: Sempre feche a conexao WS ao desmontar:
  ```typescript
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    // ...
    return () => {
      ws.close();
    };
  }, []);
  ```

---

## 4. Three.js e Renderizacao Reativa (`ArcReactor.tsx`)

Ao renderizar particulas ou anis orbitais no Three.js dentro do React, sempre realize o descarte de memoria:

```typescript
useEffect(() => {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  
  // Geometria e Material
  const geometry = new THREE.RingGeometry(1, 1.2, 32);
  const material = new THREE.MeshBasicMaterial({ color: 0x00f3ff });
  const ring = new THREE.Mesh(geometry, material);
  scene.add(ring);

  let frameId: number;
  const animate = () => {
    ring.rotation.z += 0.01;
    renderer.render(scene, camera);
    frameId = requestAnimationFrame(animate);
  };
  animate();

  return () => {
    cancelAnimationFrame(frameId);
    geometry.dispose();
    material.dispose();
    renderer.dispose();
  };
}, []);
```

---

## 5. Design System: Cyber Glassmorphism

Utilize Tailwind CSS com paleta de cores Stark/Neon:
- Bordas neon: `border border-cyan-500/30 hover:border-cyan-400`
- Fundo translucido: `bg-slate-950/80 backdrop-blur-md`
- Brilho de estado: `shadow-[0_0_15px_rgba(6,182,212,0.35)]`
