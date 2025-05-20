import { useEffect, useState, useRef } from "react";

type AudioAssistantProps = {
  onTranscription?: (text: string) => void;
  onResponse?: (text: string) => void;
};

export function useAudioAssistant({ onTranscription, onResponse }: AudioAssistantProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceOptions, setVoiceOptions] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<SpeechSynthesisVoice | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      synthRef.current = window.speechSynthesis;
      const populateVoices = () => {
        const voices = synthRef.current?.getVoices() || [];
        setVoiceOptions(voices);
        
        // Set default voice preferring English
        const englishVoice = voices.find(
          (v) => v.lang.startsWith('en-') && v.default
        );
        const defaultVoice = englishVoice || voices.find((v) => v.default) || voices[0];
        
        if (defaultVoice) {
          setSelectedVoice(defaultVoice);
        }
      };
      
      populateVoices();
      
      // Chrome loads voices asynchronously
      if (synthRef.current) {
        synthRef.current.onvoiceschanged = populateVoices;
      }
    }
    
    return () => {
      // Cancel any ongoing speech when component unmounts
      if (synthRef.current) {
        synthRef.current.cancel();
      }
      
      // Stop any ongoing listening when component unmounts
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const startListening = () => {
    if (typeof window === 'undefined') return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.error("Speech recognition not supported in this browser");
      return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    
    recognitionRef.current = recognition;
    
    recognition.onstart = () => {
      setIsListening(true);
    };
    
    recognition.onend = () => {
      setIsListening(false);
    };
    
    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
    };
    
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      if (onTranscription) {
        onTranscription(transcript);
      }
    };
    
    recognition.start();
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const speak = (text: string) => {
    if (!text || !synthRef.current) return;
    
    // Cancel any ongoing speech
    synthRef.current.cancel();
    
    setIsSpeaking(true);
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    
    utterance.onend = () => {
      setIsSpeaking(false);
    };
    
    utterance.onerror = (event) => {
      console.error("Speech synthesis error", event);
      setIsSpeaking(false);
    };
    
    synthRef.current.speak(utterance);
    
    if (onResponse) {
      onResponse(text);
    }
  };

  return {
    isListening,
    isSpeaking,
    voiceOptions,
    selectedVoice,
    setSelectedVoice,
    startListening,
    stopListening,
    speak,
  };
}
