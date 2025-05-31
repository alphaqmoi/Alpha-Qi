import { useAudioAssistant } from "@/hooks/useAudioAssistant";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useState } from "react";

type VoiceControlsProps = {
  onVoiceInput?: (text: string) => void;
};

const VoiceControls = ({ onVoiceInput }: VoiceControlsProps) => {
  const [autoPlayResponses, setAutoPlayResponses] = useState(true);
  const [testText, setTestText] = useState(
    "Hello, I'm Alpha-Q AI assistant. How can I help you today?",
  );

  const {
    isListening,
    isSpeaking,
    voiceOptions,
    selectedVoice,
    setSelectedVoice,
    startListening,
    stopListening,
    speak,
  } = useAudioAssistant({
    onTranscription: (text) => {
      if (onVoiceInput) {
        onVoiceInput(text);
      }
    },
    onResponse: () => {},
  });

  const handleVoiceChange = (value: string) => {
    const voice = voiceOptions.find((v) => v.name === value);
    if (voice) {
      setSelectedVoice(voice);
    }
  };

  const testVoice = () => {
    speak(testText);
  };

  return (
    <div className="p-4 space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-4">Voice Assistant Settings</h2>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="voice-select">Voice</Label>
            <Select
              value={selectedVoice?.name || ""}
              onValueChange={handleVoiceChange}
            >
              <SelectTrigger id="voice-select" className="w-full">
                <SelectValue placeholder="Select a voice" />
              </SelectTrigger>
              <SelectContent>
                {voiceOptions.map((voice) => (
                  <SelectItem key={voice.name} value={voice.name}>
                    {voice.name} ({voice.lang})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <Label htmlFor="auto-play">Auto-play voice responses</Label>
            <Switch
              id="auto-play"
              checked={autoPlayResponses}
              onCheckedChange={setAutoPlayResponses}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="test-text">Test text</Label>
            <textarea
              id="test-text"
              className="w-full bg-gray-800 text-light rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary min-h-[80px]"
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
            />
          </div>

          <div className="flex space-x-2">
            <Button
              className="flex-1"
              onClick={testVoice}
              disabled={isSpeaking}
            >
              {isSpeaking ? (
                <span className="flex items-center">
                  <i className="ri-volume-up-line mr-2"></i> Speaking...
                </span>
              ) : (
                <span className="flex items-center">
                  <i className="ri-play-circle-line mr-2"></i> Test Voice
                </span>
              )}
            </Button>

            <Button
              className={`flex-1 ${isListening ? "bg-accent hover:bg-accent/90" : ""}`}
              onClick={isListening ? stopListening : startListening}
            >
              {isListening ? (
                <span className="flex items-center">
                  <i className="ri-mic-fill mr-2"></i> Stop Recording
                </span>
              ) : (
                <span className="flex items-center">
                  <i className="ri-mic-line mr-2"></i> Start Recording
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceControls;
