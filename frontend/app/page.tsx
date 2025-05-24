import { VoiceInterface } from "@/components/VoiceInterface";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold mb-8 text-center">DevGenius</h1>
        <p className="text-center mb-8">
          AI-powered development assistant with voice capabilities
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-semibold mb-4">Voice Interface</h2>
            <VoiceInterface />
          </div>

          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-semibold mb-4">Features</h2>
            <ul className="list-disc list-inside space-y-2">
              <li>Voice recording and transcription</li>
              <li>Text-to-speech synthesis</li>
              <li>Multiple AI model support</li>
              <li>Real-time performance metrics</li>
              <li>Secure authentication</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  );
}
