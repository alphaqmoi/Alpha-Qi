# Alpha-Q: AI Application Builder

Alpha-Q is an intelligent application builder that leverages AI to help developers create, manage, and deploy applications efficiently.

## Features

- Natural Language & Voice AI (local text + voice)
- Persistent Memory (Supabase DB or local DB + vector store)
- Full-Stack Code Creation, Issue Fixing, Deployment
- System Control & CLI Execution
- Web Preview/Build/Deploy
- Auth + GitHub Integration
- Browser & Internet Automation
- User-Centric Learning/Context Retention

## Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)
- Hugging Face account and API token
- Google Colab account (optional, for cloud offloading)
- Supabase account (optional, for database)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/alpha-q.git
cd alpha-q
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:
```env
FLASK_APP=app.py
FLASK_ENV=development
SESSION_SECRET=your-secret-key
HUGGINGFACE_TOKEN=your-huggingface-token
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
JWT_SECRET=your-jwt-secret
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

## Usage

1. Start the development server:
```bash
flask run
```

2. Access the application at `http://localhost:5000`

3. Key endpoints:
   - `/` - Main application interface
   - `/chat` - AI chat interface
   - `/models` - Model management
   - `/system` - System monitoring
   - `/monitor` - Resource monitoring

## Project Structure

```
alpha-q/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── models.py           # Database models
├── database.py         # Database integration
├── extensions.py       # Flask extensions
├── requirements.txt    # Project dependencies
├── .env               # Environment variables
├── migrations/        # Database migrations
├── utils/            # Utility modules
│   ├── colab_integration.py
│   ├── cloud_controller.py
│   ├── cloud_offloader.py
│   └── enhanced_monitoring.py
├── routes/           # Route modules
│   └── system_routes.py
└── templates/        # HTML templates
    ├── index.html
    ├── chat.html
    ├── models.html
    └── system_manager.html
```

## Development

1. Code Style:
   - Follow PEP 8 guidelines
   - Use Black for code formatting
   - Use Flake8 for linting
   - Use MyPy for type checking

2. Testing:
```bash
pytest
```

3. Code Formatting:
```bash
black .
flake8
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
🚀 Running and Building the Project with Yarn
Replace your npm commands with their Yarn equivalents:

Run Development Server:

bash
Copy
Edit
  yarn dev
Build the Project:

bash
Copy
Edit
  yarn build
Start the Application:

bash
Copy
Edit
  yarn start
Check TypeScript Types:

bash
Copy
Edit
  yarn check
Push Database Changes (Drizzle ORM):

bash
Copy
Edit
  yarn db:push

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.
