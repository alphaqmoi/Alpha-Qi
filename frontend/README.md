# DevGenius Frontend

A modern web interface for the DevGenius AI-powered development assistant with voice capabilities.

## Features

- Voice recording and transcription
- Text-to-speech synthesis
- Multiple AI model support
- Real-time performance metrics
- Secure authentication
- Modern UI with Tailwind CSS
- TypeScript support
- Next.js framework
- **Mobile & Desktop builds:** Android (APK), Windows (EXE), Mac (DMG)
- **Remote execution:** Connects to Google Colab backend for heavy tasks
- **Auto-update:** Electron apps update from this GitHub repo

## Prerequisites

- Node.js 18.x or later
- Yarn 1.x or 3.x (recommended)
- Android Studio (for APK build)
- Xcode (for Mac/iOS build)
- Windows build tools (for EXE)

## Getting Started

1. Install dependencies:
```bash
yarn install
```

2. Create a `.env.local` file in the root directory with the following variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
COLAB_API_URL=https://<your-colab-ngrok-url>
COLAB_API_KEY=your-colab-api-key
```

3. Start the development server:
```bash
yarn dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Building for Android (APK)

1. Build the web app:
```bash
yarn build
```
2. Copy output to Capacitor:
```bash
npx cap copy android
```
3. Open Android Studio:
```bash
npx cap open android
```
4. Build APK in Android Studio.

## Building for Windows (EXE) and Mac (DMG)

1. Build the web app:
```bash
yarn build
```
2. Build Electron app:
```bash
yarn electron:build
```

- EXE will be in `dist/win-unpacked/`
- DMG will be in `dist/mac/`

## Auto-Update (Electron)

- The Electron app is configured to auto-update from this GitHub repo.
- Update the `electron.js` feed URL with your GitHub username and repo.
- Publish releases to GitHub for auto-update to work.

## Colab Backend Integration

- Start the Colab backend using the provided notebook (see `/colab_backend/server.ipynb`).
- Set `COLAB_API_URL` and `COLAB_API_KEY` in your `.env.local`.
- The app will use Colab for remote execution when selected.

## Execution Mode Toggle

- Use the dashboard to select between Local CPU, Local GPU, or Colab (remote) execution.
- Auto mode will benchmark your device and choose the best option.

## Communication Layer

- The app communicates with the Colab backend via REST API.
- All requests include the `x-api-key` header for security.

## Development

- `yarn dev` - Start development server
- `yarn build` - Build for production
- `yarn start` - Start production server
- `yarn lint` - Run ESLint
- `yarn electron:build` - Build Electron desktop app

## License

MIT
