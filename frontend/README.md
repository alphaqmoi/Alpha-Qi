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

## Prerequisites

- Node.js 18.x or later
- npm 9.x or later

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Create a `.env.local` file in the root directory with the following variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/                 # Next.js app directory
│   ├── globals.css     # Global styles
│   ├── layout.tsx      # Root layout
│   └── page.tsx        # Home page
├── components/         # React components
│   ├── ui/            # UI components
│   └── VoiceInterface.tsx
├── hooks/             # Custom React hooks
│   ├── useAuth.ts
│   ├── useModels.ts
│   └── useVoice.ts
├── lib/               # Utility functions
│   └── utils.ts
└── public/            # Static assets
```

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Dependencies

- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [Radix UI](https://www.radix-ui.com/) - Unstyled UI components
- [Lucide Icons](https://lucide.dev/) - Beautiful icons
- [TypeScript](https://www.typescriptlang.org/) - Type safety

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT 