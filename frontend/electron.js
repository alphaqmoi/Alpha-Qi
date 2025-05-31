const { app, BrowserWindow, autoUpdater } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });
  win.loadFile(path.join(__dirname, "out", "index.html"));
  // Auto-update
  win.webContents.on("did-finish-load", () => {
    autoUpdater.checkForUpdatesAndNotify();
  });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// Auto-update config
const server = "https://update.electronjs.org";
const feed = `${server}/<your-github-username>/<your-repo-name>/<platform>-<arch>/<version>`;
autoUpdater.setFeedURL({ url: feed });

autoUpdater.on("update-downloaded", () => {
  autoUpdater.quitAndInstall();
});
