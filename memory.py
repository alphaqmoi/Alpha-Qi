import json
import os
from datetime import datetime
from typing import Any, Dict, List

# Create a directory for storing conversation history
HISTORY_DIR = "conversation_history"
os.makedirs(HISTORY_DIR, exist_ok=True)


def append_conversation(user_id: str, message: str, response: Dict[str, Any]) -> None:
    """
    Append a conversation to the user's history file.

    Args:
        user_id (str): The user's unique identifier
        message (str): The user's message
        response (Dict[str, Any]): The AI's response
    """
    history_file = os.path.join(HISTORY_DIR, f"{user_id}.json")

    # Load existing history or create new
    if os.path.exists(history_file):
        with open(history_file, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    # Add new conversation
    conversation = {
        "timestamp": datetime.now().isoformat(),
        "user_message": message,
        "ai_response": response["message"],
        "model": response["model"],
        "task": response["task"],
    }

    history.append(conversation)

    # Keep only last 100 conversations
    if len(history) > 100:
        history = history[-100:]

    # Save updated history
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_conversation_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the user's conversation history.

    Args:
        user_id (str): The user's unique identifier
        limit (int): Maximum number of conversations to return

    Returns:
        List[Dict[str, Any]]: List of recent conversations
    """
    history_file = os.path.join(HISTORY_DIR, f"{user_id}.json")

    if not os.path.exists(history_file):
        return []

    with open(history_file, encoding="utf-8") as f:
        history = json.load(f)

    return history[-limit:]


def clear_conversation_history(user_id: str) -> None:
    """
    Clear the user's conversation history.

    Args:
        user_id (str): The user's unique identifier
    """
    history_file = os.path.join(HISTORY_DIR, f"{user_id}.json")

    if os.path.exists(history_file):
        os.remove(history_file)
