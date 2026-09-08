const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvisElectron', {
  minimize: () => ipcRenderer.send('window-minimize'),
  toggleMaximize: () => ipcRenderer.send('window-toggle-maximize'),
  toggleFullscreen: () => ipcRenderer.send('window-toggle-fullscreen'),
  close: () => ipcRenderer.send('window-close'),
  togglePin: (isPinned) => ipcRenderer.send('window-toggle-pin', isPinned),
});
