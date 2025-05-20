import os
import json
import logging
import base64
import time
import random

# Configure logging
logger = logging.getLogger(__name__)

class VoiceSynthesizer:
    """
    Voice synthesizer for text-to-speech capabilities.
    This uses browser's built-in speech synthesis capabilities instead of external APIs.
    """
    
    # Available voices with their characteristics
    AVAILABLE_VOICES = {
        "male_deep": {
            "id": "male_deep",
            "name": "Daniel",
            "gender": "male",
            "description": "Deep male voice with British accent",
            "lang": "en-GB",
            "browser_settings": {
                "pitch": 0.9,
                "rate": 0.9,
                "voice_name": "Daniel"
            }
        },
        "male_neutral": {
            "id": "male_neutral",
            "name": "Michael",
            "gender": "male",
            "description": "Neutral male voice with American accent",
            "lang": "en-US",
            "browser_settings": {
                "pitch": 1.0,
                "rate": 1.0,
                "voice_name": "Alex"
            }
        },
        "female_warm": {
            "id": "female_warm",
            "name": "Emily",
            "gender": "female",
            "description": "Warm female voice with British accent",
            "lang": "en-GB",
            "browser_settings": {
                "pitch": 1.1,
                "rate": 0.95,
                "voice_name": "Emily"
            }
        },
        "female_clear": {
            "id": "female_clear",
            "name": "Sophia",
            "gender": "female",
            "description": "Clear female voice with American accent",
            "lang": "en-US",
            "browser_settings": {
                "pitch": 1.0,
                "rate": 1.0,
                "voice_name": "Samantha"
            }
        },
        "neutral": {
            "id": "neutral",
            "name": "Jamie",
            "gender": "neutral",
            "description": "Neutral voice with slight British accent",
            "lang": "en-GB",
            "browser_settings": {
                "pitch": 1.05,
                "rate": 1.0,
                "voice_name": "Karen"
            }
        }
    }
    
    def __init__(self, default_voice_id="neutral"):
        """
        Initialize the Voice Synthesizer.
        
        Args:
            default_voice_id (str): ID of the default voice to use
        """
        self.default_voice_id = default_voice_id
        
        # Create cache directory if it doesn't exist
        os.makedirs("voice_cache", exist_ok=True)
    
    def list_voices(self, gender=None):
        """
        List available voices, optionally filtered by gender.
        
        Args:
            gender (str, optional): Filter by gender. Options: 'male', 'female', 'neutral'
            
        Returns:
            list: List of available voices
        """
        if gender:
            return [v for v in self.AVAILABLE_VOICES.values() if v["gender"] == gender]
        return list(self.AVAILABLE_VOICES.values())
    
    def get_voice(self, voice_id=None):
        """
        Get voice details by ID.
        
        Args:
            voice_id (str, optional): Voice ID. If None, returns default voice.
            
        Returns:
            dict: Voice details or None if not found
        """
        voice_id = voice_id or self.default_voice_id
        return self.AVAILABLE_VOICES.get(voice_id)
    
    def set_default_voice(self, voice_id):
        """
        Set the default voice.
        
        Args:
            voice_id (str): ID of the voice to set as default
            
        Returns:
            bool: True if successful, False otherwise
        """
        if voice_id in self.AVAILABLE_VOICES:
            self.default_voice_id = voice_id
            return True
        return False
    
    def synthesize_speech(self, text, voice_id=None):
        """
        Synthesize speech from text.
        
        Note: This is a server-side placeholder. In the actual app, speech synthesis
        is performed client-side using the Web Speech API.
        
        Args:
            text (str): Text to synthesize
            voice_id (str, optional): ID of the voice to use
            
        Returns:
            dict: Result of synthesis with browser settings
        """
        voice = self.get_voice(voice_id)
        if not voice:
            voice = self.get_voice(self.default_voice_id)
        
        # In a real server-side implementation, this would generate audio
        # For this demo, we'll return settings for the browser to use
        
        return {
            "status": "success",
            "message": "Use browser speech synthesis",
            "text": text,
            "voice_id": voice["id"],
            "voice_name": voice["name"],
            "voice_settings": voice["browser_settings"]
        }
    
    def split_long_text(self, text, max_length=100):
        """
        Split long text into smaller chunks for better TTS performance.
        
        Args:
            text (str): Text to split
            max_length (int): Maximum chunk length
            
        Returns:
            list: List of text chunks
        """
        # Simple splitting by sentences
        sentences = []
        current_chunk = []
        current_length = 0
        
        # Split by common sentence terminators
        for sentence in self._split_sentences(text):
            sentence_length = len(sentence)
            
            if current_length + sentence_length <= max_length:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    sentences.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
        
        if current_chunk:
            sentences.append(" ".join(current_chunk))
        
        return sentences
    
    def _split_sentences(self, text):
        """
        Split text into sentences.
        
        Args:
            text (str): Text to split
            
        Returns:
            list: List of sentences
        """
        # Simple sentence splitting by punctuation
        # This could be improved with NLP libraries in a real implementation
        text = text.replace("!", ".|").replace("?", "?|").replace(".", ".|")
        sentences = text.split("|")
        return [s.strip() for s in sentences if s.strip()]
    
    def get_voice_script(self):
        """
        Get JavaScript code for browser-side speech synthesis.
        
        Returns:
            str: JavaScript code
        """
        return """
        class VoiceSynthesis {
            constructor() {
                this.synth = window.speechSynthesis;
                this.voices = [];
                this.isPlaying = false;
                this.queue = [];
                this.currentVoiceId = 'neutral';
                
                // Load voices when available
                if (speechSynthesis.onvoiceschanged !== undefined) {
                    speechSynthesis.onvoiceschanged = this.loadVoices.bind(this);
                }
                
                this.loadVoices();
            }
            
            loadVoices() {
                this.voices = this.synth.getVoices();
                console.log(`Loaded ${this.voices.length} voices`);
            }
            
            speak(text, voiceSettings) {
                if (!text) return;
                
                // Cancel any current speech
                this.cancel();
                
                const utterance = new SpeechSynthesisUtterance(text);
                
                // Set voice if available
                if (voiceSettings && voiceSettings.voice_name) {
                    const voice = this.voices.find(v => 
                        v.name.toLowerCase().includes(voiceSettings.voice_name.toLowerCase())
                    );
                    
                    if (voice) {
                        utterance.voice = voice;
                    }
                }
                
                // Set pitch and rate
                if (voiceSettings) {
                    utterance.pitch = voiceSettings.pitch || 1;
                    utterance.rate = voiceSettings.rate || 1;
                }
                
                // Set language if not using a specific voice
                if (!utterance.voice && voiceSettings && voiceSettings.lang) {
                    utterance.lang = voiceSettings.lang;
                }
                
                // Add to queue
                this.queue.push(utterance);
                
                // Start speaking if not already playing
                if (!this.isPlaying) {
                    this.playNext();
                }
            }
            
            playNext() {
                if (this.queue.length === 0) {
                    this.isPlaying = false;
                    return;
                }
                
                this.isPlaying = true;
                const utterance = this.queue.shift();
                
                utterance.onend = () => {
                    this.playNext();
                };
                
                utterance.onerror = (e) => {
                    console.error('Speech synthesis error:', e);
                    this.playNext();
                };
                
                this.synth.speak(utterance);
            }
            
            cancel() {
                this.synth.cancel();
                this.queue = [];
                this.isPlaying = false;
            }
            
            pause() {
                this.synth.pause();
            }
            
            resume() {
                this.synth.resume();
            }
            
            setVoice(voiceId, voiceSettings) {
                this.currentVoiceId = voiceId;
                this.currentVoiceSettings = voiceSettings;
            }
            
            speakWithCurrentVoice(text) {
                this.speak(text, this.currentVoiceSettings);
            }
        }
        
        // Initialize voice synthesis
        const voiceSynth = new VoiceSynthesis();
        """