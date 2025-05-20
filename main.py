from flask import Flask, request, jsonify, Response, send_file
from flasgger import Swagger, swag_from
import logging
from hf_ai import HuggingFaceAI
from memory import append_conversation, get_conversation_history
from flask_cors import CORS
import traceback
import io
import torch
from transformers import pipeline
import soundfile as sf
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
swagger = Swagger(app)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AIApp")

# Get Hugging Face token
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if not hf_token:
    raise ValueError("HUGGINGFACE_TOKEN not found in environment variables")

# Initialize Hugging Face AI
try:
    ai = HuggingFaceAI()
    logger.info("Successfully initialized Hugging Face AI")
except Exception as e:
    logger.error(f"Failed to initialize Hugging Face AI: {str(e)}")
    raise

# Initialize speech models (optional)
stt_model = None
tts_model = None

def initialize_speech_models():
    """Initialize speech models if available."""
    global stt_model, tts_model
    try:
        # Speech-to-text model
        stt_model = pipeline(
            "automatic-speech-recognition",
            model="facebook/wav2vec2-base-960h",
            token=hf_token
        )
        # Text-to-speech model
        tts_model = pipeline(
            "text-to-speech",
            model="facebook/fastspeech2-en-ljspeech",
            token=hf_token
        )
        logger.info("Successfully initialized speech models")
        return True
    except Exception as e:
        logger.warning(f"Speech models not available: {str(e)}")
        logger.info("Speech-to-text and text-to-speech features will be disabled")
        return False

# Try to initialize speech models, but don't fail if they're not available
initialize_speech_models()

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    logger.error(f"Unhandled error: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": "An unexpected error occurred",
        "details": str(error)
    }), 500

@app.route("/ask", methods=["POST"])
@swag_from({
    'tags': ['Ask AI'],
    'parameters': [
        {
            'name': 'message',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user_id': {'type': 'string'},
                    'history': {'type': 'array'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'AI response with reasoning',
            'examples': {
                'application/json': {
                    "AI Message": "...",
                    "Reasoning": "...",
                    "Model Used": "gpt2",
                    "Task": "text-generation"
                }
            }
        },
        400: {
            'description': 'Bad request',
            'examples': {
                'application/json': {
                    "error": "Message is required"
                }
            }
        },
        500: {
            'description': 'Internal server error',
            'examples': {
                'application/json': {
                    "error": "An unexpected error occurred",
                    "details": "..."
                }
            }
        }
    }
})
def ask():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        message = data.get("message")
        user_id = data.get("user_id", "anonymous")
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "Message is required"}), 400

        response = ai.generate_response(message, conversation_history=history)
        append_conversation(user_id, message, response)

        return jsonify({
            "AI Message": response["message"],
            "Reasoning": response["reasoning"],
            "Model Used": response["model"],
            "Task": response["task"]
        })

    except Exception as e:
        logger.error(f"Error in /ask endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Failed to process request",
            "details": str(e)
        }), 500

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "")
        if not text:
            return jsonify({"error": "Text is required"}), 400

        return jsonify(ai.summarize_text(text))

    except Exception as e:
        logger.error(f"Error in /summarize endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Failed to summarize text",
            "details": str(e)
        }), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    text = request.get_json().get("text", "")
    return jsonify(ai.process_large_text(text))

@app.route("/calculate", methods=["POST"])
def calculate():
    expression = request.get_json().get("expression", "")
    return jsonify(ai.calculate_expression(expression))

@app.route("/ask_stream", methods=["POST"])
def ask_stream():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        message = data.get("message")
        history = data.get("history", [])
        if not message:
            return jsonify({"error": "Message is required"}), 400

        def generate():
            for token in ai.stream_response(message, conversation_history=history):
                yield f"data: {token}\n\n"
        return Response(generate(), mimetype="text/event-stream")
    except Exception as e:
        logger.error(f"Error in /ask_stream endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to process streaming request", "details": str(e)}), 500

@app.route("/models", methods=["GET"])
def get_models():
    """Get list of available models."""
    try:
        return jsonify(ai.get_available_models())
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/change_model", methods=["POST"])
def change_model():
    """Change the current model."""
    try:
        data = request.get_json()
        if not data or "model_name" not in data:
            return jsonify({"error": "Model name is required"}), 400
        
        success = ai.change_model(data["model_name"])
        return jsonify({"success": success, "current_model": data["model_name"]})
    except Exception as e:
        logger.error(f"Error changing model: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
def get_history():
    """Get conversation history for a user."""
    try:
        user_id = request.args.get("user_id", "anonymous")
        history = get_conversation_history(user_id)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/speech-to-text", methods=["POST"])
def speech_to_text():
    """Convert speech to text."""
    if stt_model is None:
        return jsonify({
            "error": "Speech-to-text is not available. Please check your Hugging Face token and model access."
        }), 503
    
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        audio_data, sample_rate = sf.read(audio_file)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        # Convert to float32
        audio_data = audio_data.astype(np.float32)
        
        # Perform speech recognition
        result = stt_model(audio_data)
        
        return jsonify({"text": result["text"]})
    except Exception as e:
        logger.error(f"Error in speech-to-text: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/text-to-speech", methods=["POST"])
def text_to_speech():
    """Convert text to speech."""
    if tts_model is None:
        return jsonify({
            "error": "Text-to-speech is not available. Please check your Hugging Face token and model access."
        }), 503
    
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400
        
        # Generate speech
        speech = tts_model(data["text"])
        
        # Convert to audio file
        audio_data = speech["audio"]
        sample_rate = speech["sampling_rate"]
        
        # Create in-memory file
        audio_file = io.BytesIO()
        sf.write(audio_file, audio_data, sample_rate, format="WAV")
        audio_file.seek(0)
        
        return send_file(
            audio_file,
            mimetype="audio/wav",
            as_attachment=True,
            download_name="speech.wav"
        )
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
