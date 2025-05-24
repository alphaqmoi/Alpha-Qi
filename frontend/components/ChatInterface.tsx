import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { Send, Mic, MicOff, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useModels } from "@/hooks/useModels";
import { VoiceInterface } from "./VoiceInterface";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  className?: string;
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const {
    models,
    loading: modelsLoading,
    selectedModel,
    setSelectedModel,
  } = useModels();

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Create chat session
  const createSession = async () => {
    try {
      const response = await fetch("/api/ai/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.token}`,
        },
        body: JSON.stringify({
          model_id: selectedModel?.id,
        }),
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
        description: "Failed to create chat session",
        variant: "destructive",
      });
    }
  };

  // End chat session
  const endSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`/api/ai/session/${sessionId}`, {
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

  // Send message
  const sendMessage = async (content: string) => {
    if (!sessionId || !content.trim() || isLoading) return;

    setIsLoading(true);

    try {
      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInput("");

      // Save user message
      await fetch("/api/ai/interaction", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          content,
          type: "input",
        }),
      });

      // Get model response
      const response = await fetch("/api/ai/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          prompt: content,
          model_id: selectedModel?.id,
        }),
      });

      const data = await response.json();
      if (data.status === "success") {
        // Add assistant message
        const assistantMessage: Message = {
          id: Date.now().toString(),
          role: "assistant",
          content: data.response,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Save assistant message
        await fetch("/api/ai/interaction", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${user?.token}`,
          },
          body: JSON.stringify({
            session_id: sessionId,
            content: data.response,
            type: "output",
            metadata: {
              tokens_used: data.tokens_used,
              processing_time: data.processing_time,
            },
          }),
        });
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send message",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Handle voice transcription
  const handleTranscription = (text: string) => {
    setInput(text);
  };

  return (
    <Card className={className}>
      <CardContent className="p-4">
        <div className="flex items-center space-x-2 mb-4">
          <Select
            value={selectedModel?.id}
            onValueChange={setSelectedModel}
            disabled={modelsLoading}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              {models?.map((model) => (
                <SelectItem key={model.id} value={model.id}>
                  {model.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <VoiceInterface
            onTranscription={handleTranscription}
            className="flex-1"
          />
        </div>

        <div className="h-[400px] overflow-y-auto mb-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {message.content}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex space-x-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(input);
              }
            }}
          />

          <Button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
