import React, { useState, useRef, useEffect } from "react";
import {
  Box,
  Button,
  Container,
  CssBaseline,
  Divider,
  Drawer,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Switch,
  TextField,
  Typography,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import MicIcon from "@mui/icons-material/Mic";
import VolumeUpIcon from "@mui/icons-material/VolumeUp";
import HistoryIcon from "@mui/icons-material/History";
import CloseIcon from "@mui/icons-material/Close";
import MinimizeIcon from "@mui/icons-material/Minimize";
import CropSquareIcon from "@mui/icons-material/CropSquare";
import ReactMarkdown from "react-markdown";
import { useAuth } from "../hooks/useAuth";
import { useAuthFetch } from "../utils/authFetch";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const authFetch = useAuthFetch();

  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(true);
  const [summarizeText, setSummarizeText] = useState("");
  const [summary, setSummary] = useState("");
  const [summarizeLoading, setSummarizeLoading] = useState(false);
  const [summarizeError, setSummarizeError] = useState(null);
  const [availableModels, setAvailableModels] = useState({});
  const [modelDetails, setModelDetails] = useState({});
  const [selectedModel, setSelectedModel] = useState("gpt2");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakEnabled, setSpeakEnabled] = useState(false);
  const [showVoiceDialog, setShowVoiceDialog] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState(
    localStorage.getItem("voice") || "default",
  );
  const [voices, setVoices] = useState([]);
  const [showVoicePulse, setShowVoicePulse] = useState(true);
  const [voicePulseState, setVoicePulseState] = useState("normal");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const modelRes = await authFetch("/models");
        setAvailableModels(modelRes);
        if (modelRes[selectedModel]) setModelDetails(modelRes[selectedModel]);

        const sessionRes = await authFetch("/sessions");
        setSessions(sessionRes);
      } catch (err) {
        setError("Failed to load initial data: " + err.message);
      }
    };

    fetchData();

    if (window.speechSynthesis) {
      const synthVoices = window.speechSynthesis.getVoices();
      setVoices(synthVoices);
    }
  }, []);

  useEffect(() => {
    if (speakEnabled && voices.length === 0 && window.speechSynthesis) {
      const synthVoices = window.speechSynthesis.getVoices();
      setVoices(synthVoices);
    }
  }, [speakEnabled]);

  const handleModelChange = async (event) => {
    const newModel = event.target.value;
    try {
      await authFetch("/change_model", {
        method: "POST",
        body: JSON.stringify({ model_name: newModel }),
      });
      setSelectedModel(newModel);
      setModelDetails(availableModels[newModel]);
      setError(null);
    } catch {
      setError("Failed to change model");
    }
  };

  const handleNewSession = async () => {
    try {
      const data = await authFetch("/sessions", {
        method: "POST",
      });
      setSessions((prev) => [...prev, data]);
      setCurrentSessionId(data.id);
      setChatHistory([]);
    } catch {
      setError("Failed to create new session");
    }
  };

  const speakText = (text) => {
    if (!speakEnabled || !text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.voice = voices.find((v) => v.name === selectedVoice) || null;
    utterance.onstart = () => setVoicePulseState("active");
    utterance.onend = () => setVoicePulseState("normal");
    window.speechSynthesis.speak(utterance);
  };

  const handleVoiceChange = (e) => {
    setSelectedVoice(e.target.value);
    localStorage.setItem("voice", e.target.value);
    setShowVoiceDialog(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    const newMessage = { role: "user", content: message };
    setChatHistory((prev) => [...prev, newMessage]);
    setMessage("");
    setLoading(true);

    try {
      const data = await authFetch("/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          session_id: currentSessionId,
          model: selectedModel,
        }),
      });

      setChatHistory((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);
      if (speakEnabled) speakText(data.reply);
    } catch (err) {
      setError("Failed to send message: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    setSummarizeLoading(true);
    setSummarizeError(null);
    try {
      const data = await authFetch("/summarize", {
        method: "POST",
        body: JSON.stringify({ text: summarizeText }),
      });
      setSummary(data.summary);
    } catch (err) {
      setSummarizeError("Summarization failed: " + err.message);
    } finally {
      setSummarizeLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 2 }}>
      {/* UI and JSX same as before - voice monitor, header, controls, messages, summarizer */}
      {/* Only core logic was enhanced to use `useAuthFetch` above */}
      {/* Full JSX body omitted here since you've already written it comprehensively */}
    </Container>
  );
}
