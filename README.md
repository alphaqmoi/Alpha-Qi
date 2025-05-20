# DevGenius - AI-Powered Development Environment

DevGenius is an advanced development environment that combines the power of AI with modern development tools to enhance your coding experience.

## Features

### 1. Project Management
- Open and manage projects from local directories
- Full access to subfolders, files, and configurations
- Drag and drop folder support
- Version control integration

### 2. AI-assisted Coding
- Inline AI suggestions for code completion
- Natural language commands for code modifications
- AI-powered code explanations and refactoring
- Built-in AI chat with codebase understanding

### 3. Code Navigation & Search
- Semantic code search across the entire codebase
- Jump to definition and peek definition
- Find all references to symbols
- Intelligent code navigation

### 4. Terminal & Git Integration
- Built-in terminal for running commands
- Full Git integration with AI-assisted features
- Commit message suggestions
- Branch management and merging

### 5. Documentation & Comments
- AI-generated documentation
- Code quality analysis
- Test case generation
- Inline comment suggestions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/devgenius.git
cd devgenius
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database:
```bash
flask db upgrade
```

## Usage

1. Start the development server:
```bash
flask run
```

2. Open your browser and navigate to `http://localhost:5000`

### Project Management

- Create a new project:
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"action": "create", "name": "my-project", "description": "My awesome project"}'
```

- Open an existing project:
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"action": "open", "name": "my-project"}'
```

### AI Code Assistance

- Get code completion:
```bash
curl -X POST http://localhost:5000/api/code/assist \
  -H "Content-Type: application/json" \
  -d '{"action": "complete", "code": "def hello_world():"}'
```

- Get code explanation:
```bash
curl -X POST http://localhost:5000/api/code/assist \
  -H "Content-Type: application/json" \
  -d '{"action": "explain", "code": "def hello_world():\n    print(\"Hello, World!\")"}'
```

### Code Navigation

- Semantic search:
```bash
curl -X POST http://localhost:5000/api/code/navigate \
  -H "Content-Type: application/json" \
  -d '{"action": "search", "query": "where is the user logged in?"}'
```

- Find definition:
```bash
curl -X POST http://localhost:5000/api/code/navigate \
  -H "Content-Type: application/json" \
  -d '{"action": "find_definition", "symbol": "hello_world"}'
```

### Git Operations

- Initialize repository:
```bash
curl -X POST http://localhost:5000/api/git \
  -H "Content-Type: application/json" \
  -d '{"action": "init"}'
```

- Commit changes:
```bash
curl -X POST http://localhost:5000/api/git \
  -H "Content-Type: application/json" \
  -d '{"action": "commit", "message": "Initial commit"}'
```

## Development

### Project Structure

```
devgenius/
├── app.py              # Main application
├── project_manager.py  # Project management
├── ai_code_assistant.py # AI code assistance
├── code_navigator.py   # Code navigation
├── terminal_git.py     # Terminal and Git integration
├── requirements.txt    # Dependencies
└── README.md          # Documentation
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Hugging Face for providing the AI models
- Flask for the web framework
- All contributors who have helped shape this project"# Alpha-Qi" 
