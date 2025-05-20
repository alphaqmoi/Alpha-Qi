import React, { useState, useRef, useEffect } from 'react';
import {
  Container,
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Switch,
  FormControlLabel,
  Divider,
  Select,
  MenuItem,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import MicIcon from '@mui/icons-material/Mic';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import HistoryIcon from '@mui/icons-material/History';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
  },
});

function App() {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(true);
  const [summarizeText, setSummarizeText] = useState('');
  const [summary, setSummary] = useState('');
  const [summarizeLoading, setSummarizeLoading] = useState(false);
  const [summarizeError, setSummarizeError] = useState(null);
  const [availableModels, setAvailableModels] = useState({});
  const [selectedModel, setSelectedModel] = useState('gpt2');
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const eventSourceRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // Load available models
    fetch('/models')
      .then(res => res.json())
      .then(data => setAvailableModels(data))
      .catch(err => setError('Failed to load models'));
  }, []);

  const handleModelChange = async (event) => {
    const newModel = event.target.value;
    try {
      const response = await fetch('/change_model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: newModel }),
      });
      if (response.ok) {
        setSelectedModel(newModel);
      }
    } catch (err) {
      setError('Failed to change model');
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('audio', audioBlob);

        try {
          const response = await fetch('/speech-to-text', {
            method: 'POST',
            body: formData,
          });
          const data = await response.json();
          setMessage(data.text);
        } catch (err) {
          setError('Failed to convert speech to text');
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      setError('Failed to access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const speakText = async (text) => {
    if (isSpeaking) return;
    setIsSpeaking(true);
    try {
      const response = await fetch('/text-to-speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.onended = () => setIsSpeaking(false);
      audio.play();
    } catch (err) {
      setError('Failed to convert text to speech');
      setIsSpeaking(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    setError(null);

    if (streaming) {
      let assistantMsg = '';
      setChatHistory((prev) => [
        ...prev,
        { role: 'user', content: message },
        { role: 'assistant', content: '' },
      ]);
      try {
        const response = await fetch('/ask_stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, history: chatHistory }),
        });
        if (!response.body) throw new Error('No response body');
        const reader = response.body.getReader();
        let done = false;
        while (!done) {
          const { value, done: doneReading } = await reader.read();
          done = doneReading;
          if (value) {
            const chunk = new TextDecoder().decode(value);
            chunk.split('data: ').forEach((token) => {
              if (token.trim()) {
                assistantMsg += token.replace(/\n/g, '');
                setChatHistory((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    content: assistantMsg,
                  };
                  return updated;
                });
              }
            });
          }
        }
        setMessage('');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    } else {
      try {
        const response = await fetch('/ask', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message,
            history: chatHistory,
          }),
        });
        if (!response.ok) {
          throw new Error('Failed to get response');
        }
        const data = await response.json();
        setChatHistory([
          ...chatHistory,
          { role: 'user', content: message },
          { role: 'assistant', content: data['AI Message'] },
        ]);
        setMessage('');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleSummarize = async () => {
    setSummarizeLoading(true);
    setSummarizeError(null);
    setSummary('');
    try {
      const res = await axios.post('/summarize', { text: summarizeText });
      setSummary(res.data.summary);
    } catch (err) {
      setSummarizeError(err.response?.data?.error || err.message);
    } finally {
      setSummarizeLoading(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="md" sx={{ height: '100vh', py: 4 }}>
        <Paper
          elevation={3}
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <Box sx={{ p: 2, bgcolor: 'primary.main', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h5" component="h1" color="white">
              AI Chat
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Select
                value={selectedModel}
                onChange={handleModelChange}
                size="small"
                sx={{ bgcolor: 'white', minWidth: 150 }}
              >
                {Object.entries(availableModels).map(([id, name]) => (
                  <MenuItem key={id} value={id}>{name}</MenuItem>
                ))}
              </Select>
              <FormControlLabel
                control={<Switch checked={streaming} onChange={() => setStreaming((v) => !v)} color="secondary" />}
                label="Streaming"
                sx={{ color: 'white' }}
              />
              <IconButton onClick={() => setHistoryDrawerOpen(true)} color="inherit">
                <HistoryIcon />
              </IconButton>
            </Box>
          </Box>

          <Box
            sx={{
              flex: 1,
              overflow: 'auto',
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
          >
            {chatHistory.map((msg, index) => (
              <Box
                key={index}
                sx={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '70%',
                }}
              >
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    bgcolor: msg.role === 'user' ? 'primary.main' : 'background.paper',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                    {msg.role === 'assistant' && (
                      <IconButton
                        size="small"
                        onClick={() => speakText(msg.content)}
                        disabled={isSpeaking}
                      >
                        <VolumeUpIcon />
                      </IconButton>
                    )}
                  </Box>
                </Paper>
              </Box>
            ))}
            {loading && (
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </Box>
            )}
            {error && (
              <Typography color="error" sx={{ textAlign: 'center' }}>
                {error}
              </Typography>
            )}
          </Box>

          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
              p: 2,
              bgcolor: 'background.paper',
              borderTop: 1,
              borderColor: 'divider',
              display: 'flex',
              gap: 1,
            }}
          >
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Type your message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={loading}
              size="small"
            />
            <IconButton
              onClick={isRecording ? stopRecording : startRecording}
              color={isRecording ? "error" : "primary"}
              disabled={loading}
            >
              <MicIcon />
            </IconButton>
            <Button
              type="submit"
              variant="contained"
              disabled={loading || !message.trim()}
              endIcon={<SendIcon />}
            >
              Send
            </Button>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Summarize Text
            </Typography>
            <TextField
              fullWidth
              multiline
              minRows={3}
              maxRows={8}
              placeholder="Paste text to summarize..."
              value={summarizeText}
              onChange={(e) => setSummarizeText(e.target.value)}
              disabled={summarizeLoading}
            />
            <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
              <Button
                variant="contained"
                color="secondary"
                onClick={handleSummarize}
                disabled={summarizeLoading || !summarizeText.trim()}
              >
                Summarize
              </Button>
              {summarizeLoading && <CircularProgress size={24} />}
            </Box>
            {summary && (
              <Paper sx={{ mt: 2, p: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Summary:
                </Typography>
                <ReactMarkdown>{summary}</ReactMarkdown>
              </Paper>
            )}
            {summarizeError && (
              <Typography color="error" sx={{ mt: 1 }}>
                {summarizeError}
              </Typography>
            )}
          </Box>
        </Paper>

        <Drawer
          anchor="right"
          open={historyDrawerOpen}
          onClose={() => setHistoryDrawerOpen(false)}
        >
          <Box sx={{ width: 300, p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Conversation History
            </Typography>
            <List>
              {chatHistory.map((msg, index) => (
                <ListItem key={index} divider>
                  <ListItemText
                    primary={msg.role === 'user' ? 'You' : 'AI'}
                    secondary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2">{msg.content}</Typography>
                        {msg.role === 'assistant' && (
                          <IconButton
                            size="small"
                            onClick={() => speakText(msg.content)}
                            disabled={isSpeaking}
                          >
                            <VolumeUpIcon />
                          </IconButton>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>
      </Container>
    </ThemeProvider>
  );
}

export default App; 