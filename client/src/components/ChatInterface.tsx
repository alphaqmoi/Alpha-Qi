import { useState, useRef } from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAudioAssistant } from "@/hooks/useAudioAssistant";
import { apiRequest } from "@/lib/queryClient";

type Message = {
  id: string;
  content: string;
  sender: "user" | "ai";
  isVoice?: boolean;
};

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Welcome to Alpha-Q AI! How can I help you with your development today?",
      sender: "ai"
    }
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { 
    isListening, 
    isSpeaking,
    voiceOptions,
    selectedVoice,
    setSelectedVoice,
    startListening,
    stopListening,
    speak
  } = useAudioAssistant({
    onTranscription: (text) => {
      sendMessage(text, true);
    },
    onResponse: () => {}
  });

  const sendMessage = async (content: string, isVoice = false) => {
    if (!content.trim()) return;
    
    // Add user message to chat
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      sender: "user",
      isVoice
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);
    
    try {
      // Send message to backend
      const response = await apiRequest("POST", "/api/chat", { message: content });
      const data = await response.json();
      
      // Add AI response to chat
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response,
        sender: "ai"
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
      // Read out response if voice was used
      if (isVoice && selectedVoice) {
        speak(data.response);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "Sorry, there was an error processing your request. Please try again.",
        sender: "ai"
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
      scrollToBottom();
    }
  };

  const handleInputKeydown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputMessage);
    }
  };

  const toggleVoiceRecording = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-3 bg-darker border-b border-gray-800 flex items-center justify-between">
        <h3 className="font-semibold text-sm">AI ASSISTANT</h3>
        <div className="flex items-center space-x-2">
          <Select 
            value={selectedVoice?.name || ""}
            onValueChange={(value) => {
              const voice = voiceOptions.find(v => v.name === value);
              if (voice) setSelectedVoice(voice);
            }}
          >
            <SelectTrigger className="bg-dark text-xs rounded border border-gray-700 px-2 py-1 h-8 w-44">
              <SelectValue placeholder="Select voice" />
            </SelectTrigger>
            <SelectContent>
              {voiceOptions.map((voice) => (
                <SelectItem key={voice.name} value={voice.name}>
                  {voice.name} ({voice.lang})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <button className="p-1 rounded hover:bg-gray-800" title="Voice Settings">
            <i className="ri-equalizer-line text-sm"></i>
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`flex items-start ${message.sender === "user" ? "justify-end" : ""}`}
          >
            {message.sender === "ai" && (
              <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center">
                <i className="ri-robot-line text-white"></i>
              </div>
            )}
            
            <div 
              className={`ml-3 ${message.sender === "ai" ? "bg-gray-800" : "bg-primary bg-opacity-20"} rounded-lg p-3 max-w-[85%] ${message.sender === "user" ? "mr-3" : ""}`}
            >
              {message.isVoice && message.sender === "user" && (
                <i className="ri-sound-module-line mr-2"></i>
              )}
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
            
            {message.sender === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex-shrink-0 flex items-center justify-center">
                <i className="ri-user-line"></i>
              </div>
            )}
          </div>
        ))}
        
        {isTyping && (
          <div className="flex items-start">
            <div className="w-8 h-8 rounded-full bg-primary flex-shrink-0 flex items-center justify-center">
              <i className="ri-robot-line text-white"></i>
            </div>
            <div className="ml-3 bg-gray-800 rounded-lg p-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse"></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-75"></div>
                <div className="w-2 h-2 rounded-full bg-gray-500 animate-pulse delay-150"></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center">
          <div className="flex-1 relative">
            <input 
              type="text" 
              className="w-full bg-gray-800 text-light rounded-l-lg px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary" 
              placeholder="Ask a question or type a command..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleInputKeydown}
            />
            <button className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 rounded hover:bg-gray-700" title="Code Suggestions">
              <i className="ri-code-box-line text-gray-400"></i>
            </button>
          </div>
          <button 
            className="bg-primary hover:bg-primary-dark text-white rounded-r-lg px-4 py-3 flex items-center justify-center" 
            onClick={() => sendMessage(inputMessage)}
          >
            <i className="ri-send-plane-fill"></i>
          </button>
        </div>
        
        <div className="flex mt-2 justify-between">
          <div className="flex space-x-2">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button 
                    className={`p-2 rounded-full ${isListening ? 'bg-accent' : 'bg-gray-800 hover:bg-gray-700'} flex items-center justify-center`}
                    onClick={toggleVoiceRecording}
                  >
                    <i className={`${isListening ? 'ri-mic-fill text-white' : 'ri-mic-line text-gray-400'}`}></i>
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{isListening ? 'Stop recording' : 'Start voice recording'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            
            <button className="p-2 rounded-full bg-gray-800 hover:bg-gray-700" title="Upload File">
              <i className="ri-attachment-line text-gray-400"></i>
            </button>
          </div>
          <div>
            <button className="text-xs text-gray-400 hover:text-light" title="AI Settings">
              <i className="ri-settings-3-line mr-1"></i> 
              <span>Settings</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
