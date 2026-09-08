---
name: threejs-hud-optimization
description: >-
  Tecnicas de alta performance para Three.js no HUD Electron do J.A.R.V.I.S: render loop adaptativo,
  framerate capping (30 FPS ocioso vs 60 FPS ativo), descarte de memoria de geometrias e materiais,
  e shaders leves sem sobrecarregar a GPU do usuario.
---

# Three.js HUD Optimization (Electron & WebGL)

O HUD do J.A.R.V.I.S utiliza WebGL e Three.js (`hud/src/components/ArcReactor.tsx`) renderizado sobre uma janela transparente do Electron. Para garantir que o assistente opere 24/7 sem consumir CPU/GPU excessiva, estas regras s?o mandat?rias.

---

## 1. Render Loop Adaptativo com Throttling de FPS

Em repouso (estado `IDLE`), o ArcReactor n?o precisa rodar a 120 FPS ou 60 FPS desnecessariamente:

```typescript
// Taxa de atualizacao dinamica baseada no estado do agente
const targetFPS = (agentState === 'SPEAKING' || agentState === 'PROCESSING') ? 60 : 24;
const frameInterval = 1000 / targetFPS;
let lastTime = 0;

function animate(now: number) {
  frameId = requestAnimationFrame(animate);
  const delta = now - lastTime;
  if (delta < frameInterval) return;
  lastTime = now - (delta % frameInterval);

  // Rotacao suave das particulas e an?is
  ring.rotation.z += 0.005;
  renderer.render(scene, camera);
}
```

---

## 2. Descarte Obrigat?rio no Cleanup do React

Para evitar memory leak de VRAM durante hot-reload ou troca de componentes:

```typescript
useEffect(() => {
  // Inicializacao...
  
  return () => {
    cancelAnimationFrame(frameId);
    geometry.dispose();
    material.dispose();
    renderer.dispose();
    if (mountRef.current && renderer.domElement) {
      mountRef.current.removeChild(renderer.domElement);
    }
  };
}, []);
```

---

## 3. Desligamento em Background

Quando o HUD for minimizado ou oculto via atalho `Ctrl+Shift+J`, o loop de anima??o do Three.js deve ser pausado imediatamente para zerar o uso da GPU.