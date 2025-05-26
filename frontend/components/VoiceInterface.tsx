'use client';

import React, { useState, useCallback, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { Mic, MicOff, Play, Pause, Square, Volume2, VolumeX } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useVoice } from "@/hooks/useVoice";
import { useModels } from "@/hooks/useModels";

interface VoiceInterfaceProps {
  onTranscription: (text: string) => void;
  onSynthesis?: (audioUrl: string) => void;
  className?: string;
}

export function VoiceInterface({
  onTranscription,
  onSynthesis,
  className,
}: VoiceInterfaceProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const { models, loading: modelsLoading } = useModels();

  // Voice state
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("auto");
  const [transcription, setTranscription] = useState("");
  const [synthesis, setSynthesis] = useState("");

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Speech recognition state
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(
    null,
  );

  // Initialize session
  useEffect(() => {
    if (user) {
      createSession();
    }
    return () => {
      if (sessionId) {
        endSession();
      }
    };
  }, [user]);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window !== "undefined" && "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join("");

        if (event.results[0].isFinal) {
          onTranscription(transcript);
        }
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        toast({
          title: "Error",
          description: "Speech recognition failed",
          variant: "destructive",
        });
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      setRecognition(recognition);
    }

    return () => {
      if (recognition) {
        recognition.stop();
      }
    };
  }, []);

  // Create voice session
  const createSession = async () => {
    try {
      const response = await fetch("/api/voice/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.token}`,
        },
      });

      const data = await response.json();
      if (data.status === "success") {
        setSessionId(data.session_id);
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create voice session",
        variant: "destructive",
      });
    }
  };

  // End voice session
  const endSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`/api/voice/session/${sessionId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      });
      setSessionId(null);
    } catch (error) {
      console.error("Error ending session:", error);
    }
  };

  // Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/wav",
        });
        await uploadAudio(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start recording",
        variant: "destructive",
      });
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach((track) => track.stop());
      setIsRecording(false);
    }
  };

  // Upload audio for transcription
  const uploadAudio = async (audioBlob: Blob) => {
    if (!sessionId) return;

    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.wav");
      formData.append("session_id", sessionId);

      const response = await fetch("/api/voice/transcribe", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (data.status === "success") {
        setTranscription(data.transcription);
        onTranscription(data.transcription);
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to transcribe audio",
        variant: "destructive",
      });
    }
  };

  // Synthesize text to speech
  const synthesizeSpeech = async () => {
    if (!sessionId || !synthesis) return;

    try {
      const response = await fetch("/api/voice/synthesize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.token}`,
        },
        body: JSON.stringify({
          text: synthesis,
          session_id: sessionId,
          language: "en",
        }),
      });

      const data = await response.json();
      if (data.status === "success") {
        // Create audio player if needed
        if (!audioPlayerRef.current) {
          audioPlayerRef.current = new Audio();
          audioPlayerRef.current.onended = () => setIsPlaying(false);
        }

        // Set audio source and play
        audioPlayerRef.current.src = data.file_path;
        audioPlayerRef.current.muted = isMuted;
        await audioPlayerRef.current.play();
        setIsPlaying(true);

        onSynthesis?.(data.file_path);
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to synthesize speech",
        variant: "destructive",
      });
    }
  };

  // Toggle audio playback
  const togglePlayback = () => {
    if (!audioPlayerRef.current) return;

    if (isPlaying) {
      audioPlayerRef.current.pause();
    } else {
      audioPlayerRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  // Toggle mute
  const toggleMute = () => {
    if (!audioPlayerRef.current) return;

    audioPlayerRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  // Toggle listening
  const toggleListening = useCallback(() => {
    if (!recognition) {
      toast({
        title: "Error",
        description: "Speech recognition not supported",
        variant: "destructive",
      });
      return;
    }

    if (isListening) {
      recognition.stop();
    } else {
      try {
        recognition.start();
        setIsListening(true);
      } catch (error) {
        console.error("Error starting speech recognition:", error);
        toast({
          title: "Error",
          description: "Failed to start speech recognition",
          variant: "destructive",
        });
      }
    }
  }, [recognition, isListening]);

  return (
    <Card className={className}>
      <CardContent className="p-4">
        <Tabs defaultValue="record" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="record">Record</TabsTrigger>
            <TabsTrigger value="synthesize">Synthesize</TabsTrigger>
          </TabsList>

          <TabsContent value="record" className="space-y-4">
            <div className="flex items-center space-x-2">
              <Select
                value={selectedModel}
                onValueChange={setSelectedModel}
                disabled={modelsLoading}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  {models?.map((model) => (
                    <SelectItem key={model.id} value={model.name}>
                      {model.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant={isRecording ? "destructive" : "default"}
                onClick={isRecording ? stopRecording : startRecording}
                disabled={!sessionId}
              >
                {isRecording ? (
                  <>
                    <Square className="mr-2 h-4 w-4" />
                    Stop
                  </>
                ) : (
                  <>
                    <Mic className="mr-2 h-4 w-4" />
                    Record
                  </>
                )}
              </Button>
            </div>

            <Textarea
              value={transcription}
              onChange={(e) => setTranscription(e.target.value)}
              placeholder="Transcription will appear here..."
              className="min-h-[100px]"
            />
          </TabsContent>

          <TabsContent value="synthesize" className="space-y-4">
            <Textarea
              value={synthesis}
              onChange={(e) => setSynthesis(e.target.value)}
              placeholder="Enter text to synthesize..."
              className="min-h-[100px]"
            />

            <div className="flex items-center space-x-2">
              <Button
                onClick={synthesizeSpeech}
                disabled={!synthesis || !sessionId}
              >
                <Volume2 className="mr-2 h-4 w-4" />
                Synthesize
              </Button>

              {audioPlayerRef.current && (
                <>
                  <Button variant="outline" onClick={togglePlayback}>
                    {isPlaying ? (
                      <Pause className="h-4 w-4" />
                    ) : (
                      <Play className="h-4 w-4" />
                    )}
                  </Button>

                  <Button variant="outline" onClick={toggleMute}>
                    {isMuted ? (
                      <VolumeX className="h-4 w-4" />
                    ) : (
                      <Volume2 className="h-4 w-4" />
                    )}
                  </Button>
                </>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// Add TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}
