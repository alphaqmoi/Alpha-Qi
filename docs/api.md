# Alpha-Q API Documentation

## Authentication

All API endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

## Base URL

- Development: `http://localhost:5000/api/v1`
- Production: `https://api.alpha-q.com/v1`

## Endpoints

### Authentication

#### POST /auth/login

Authenticate user and get JWT token.

**Request:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**

```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /auth/refresh

Refresh JWT token.

**Request:**

```json
{
  "refresh_token": "string"
}
```

**Response:**

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### AI Models

#### GET /models

List available AI models.

**Response:**

```json
{
  "models": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "status": "string",
      "parameters": {
        "size": "string",
        "quantization": "string",
        "framework": "string"
      }
    }
  ]
}
```

#### POST /models/load

Load a specific model.

**Request:**

```json
{
  "model_id": "string",
  "parameters": {
    "device": "string",
    "quantization": "string"
  }
}
```

**Response:**

```json
{
  "status": "string",
  "model_id": "string",
  "load_time": "float"
}
```

### Chat Interface

#### POST /chat/completion

Get AI model completion.

**Request:**

```json
{
  "prompt": "string",
  "model_id": "string",
  "parameters": {
    "temperature": "float",
    "max_tokens": "integer",
    "top_p": "float"
  }
}
```

**Response:**

```json
{
  "completion": "string",
  "model_id": "string",
  "usage": {
    "prompt_tokens": "integer",
    "completion_tokens": "integer",
    "total_tokens": "integer"
  }
}
```

### System Management

#### GET /system/status

Get system status and resource usage.

**Response:**

```json
{
  "status": "string",
  "resources": {
    "cpu": {
      "usage": "float",
      "temperature": "float"
    },
    "memory": {
      "total": "integer",
      "used": "integer",
      "free": "integer"
    },
    "gpu": {
      "usage": "float",
      "memory_used": "integer",
      "memory_total": "integer"
    }
  },
  "models": {
    "loaded": ["string"],
    "cached": ["string"]
  }
}
```

#### POST /system/colab/connect

Connect to Google Colab.

**Request:**

```json
{
  "credentials": {
    "client_id": "string",
    "client_secret": "string"
  }
}
```

**Response:**

```json
{
  "status": "string",
  "runtime_info": {
    "type": "string",
    "gpu": "string",
    "memory": "integer"
  }
}
```

### Database Management

#### GET /db/backup

List database backups.

**Response:**

```json
{
  "backups": [
    {
      "id": "string",
      "timestamp": "string",
      "size": "integer",
      "status": "string"
    }
  ]
}
```

#### POST /db/backup

Create new database backup.

**Response:**

```json
{
  "backup_id": "string",
  "status": "string",
  "timestamp": "string"
}
```

#### POST /db/restore/{backup_id}

Restore database from backup.

**Response:**

```json
{
  "status": "string",
  "restored_at": "string"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "error": "string",
  "message": "string",
  "details": {}
}
```

### 401 Unauthorized

```json
{
  "error": "unauthorized",
  "message": "Invalid or expired token"
}
```

### 403 Forbidden

```json
{
  "error": "forbidden",
  "message": "Insufficient permissions"
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Resource not found"
}
```

### 429 Too Many Requests

```json
{
  "error": "rate_limit",
  "message": "Rate limit exceeded",
  "retry_after": "integer"
}
```

### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "message": "Internal server error",
  "request_id": "string"
}
```

## Rate Limiting

API requests are rate-limited based on the endpoint and user tier:

- Free tier: 100 requests/minute
- Pro tier: 1000 requests/minute
- Enterprise tier: Custom limits

Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1612345678
```

## WebSocket API

### Connection

Connect to WebSocket endpoint:

```javascript
const ws = new WebSocket("ws://localhost:5000/ws");
```

### Events

#### chat.stream

Stream chat completions in real-time.

**Request:**

```json
{
  "event": "chat.stream",
  "data": {
    "prompt": "string",
    "model_id": "string"
  }
}
```

**Response:**

```json
{
  "event": "chat.stream",
  "data": {
    "token": "string",
    "is_final": "boolean"
  }
}
```

#### system.status

Subscribe to system status updates.

**Request:**

```json
{
  "event": "system.status",
  "data": {
    "interval": "integer"
  }
}
```

**Response:**

```json
{
  "event": "system.status",
  "data": {
    "resources": {
      "cpu": "float",
      "memory": "integer",
      "gpu": "float"
    }
  }
}
```

## SDK Examples

### Python

```python
from alpha_q import AlphaQClient

client = AlphaQClient(api_key="your_api_key")

# Chat completion
response = client.chat.completion(
    prompt="Hello, how are you?",
    model_id="gpt-3.5-turbo"
)
print(response.completion)

# System status
status = client.system.status()
print(status.resources)
```

### JavaScript

```javascript
import { AlphaQClient } from "@alpha-q/client";

const client = new AlphaQClient("your_api_key");

// Chat completion
const response = await client.chat.completion({
  prompt: "Hello, how are you?",
  modelId: "gpt-3.5-turbo",
});
console.log(response.completion);

// System status
const status = await client.system.status();
console.log(status.resources);
```
