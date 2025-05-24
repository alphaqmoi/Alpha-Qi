# Alpha-Q: AI Application Builder

Alpha-Q is an intelligent application builder that leverages AI to help developers create, manage, and deploy applications efficiently.

---

## ✨ Features

* 🧐 Natural Language & Voice AI (local text + voice)
* 📀 Persistent Memory (Supabase DB or local DB + vector store)
* 💻 Full-Stack Code Creation, Issue Fixing, Deployment
* 🖥️ System Control & CLI Execution
* 🌐 Web Preview, Build & Deploy
* 🔐 Auth + GitHub Integration
* 🤸‍ Browser & Internet Automation
* 🧕 User-Centric Learning & Context Retention

---

## ✅ Prerequisites

* Python 3.11+
* Git
* Virtual environment (recommended)
* Hugging Face account and API token
* Google Colab account (optional, for cloud offloading)
* Supabase account (optional, for database)

---

## ⚙️ Installation

### 1. Clone the repository:

```bash
git clone https://github.com/yourusername/alpha-q.git
cd alpha-q
```

### 2. Run the setup script (recommended):

```bash
./setup-dev.sh  # For macOS/Linux
# or on Windows (CMD):
setup-dev.bat
```

<details>
<summary>🔧 Manual setup (if not using the script)</summary>

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
pre-commit autoupdate
```

</details>

---

### 3. Add a `.env` file:

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

---

### 4. Initialize the database:

```bash
flask db upgrade
```

---

## 🧪 Development

### 🔨 Commands

| Action         | Command             |
| -------------- | ------------------- |
| Setup          | `make setup`        |
| Run app        | `make run`          |
| Run prod app   | `make run-prod`     |
| Lint code      | `make lint`         |
| Format code    | `make format`       |
| Run tests      | `make test`         |
| Clean project  | `make clean`        |
| Build Docker   | `make docker-build` |
| Up Docker      | `make docker-up`    |
| Down Docker    | `make docker-down`  |
| DB Migrate     | `make migrate`      |
| Init AI Models | `make init-models`  |

---

## 📂 Project Structure

```
alpha-q/
├── app.py
├── config.py
├── models.py
├── database.py
├── extensions.py
├── requirements*.txt
├── .env
├── migrations/
├── scripts/
│   └── init_models.py
├── utils/
│   ├── colab_integration.py
│   ├── cloud_controller.py
│   ├── cloud_offloader.py
│   └── enhanced_monitoring.py
├── routes/
│   └── system_routes.py
├── templates/
│   ├── index.html
│   ├── chat.html
│   ├── models.html
│   └── system_manager.html
```

---

## 🌐 Web Interface

* `/` - Main app interface
* `/chat` - AI chat
* `/models` - Model manager
* `/system` - System control
* `/monitor` - Monitoring dashboard

---

## 🧪 Testing & Formatting

```bash
pytest              # Run tests
black .             # Format code
flake8              # Lint
mypy .              # Type check
```

---

## 📦 Yarn-based Web Interface (optional frontend)

```bash
yarn dev        # Start dev server
yarn build      # Build production assets
yarn start      # Start production server
yarn check      # TypeScript check
yarn db:push    # Push DB changes (Drizzle ORM)
```

---

## 👍 Contributing

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push and open a PR

---

## 📄 License

MIT License — see `LICENSE` for full details.

---

## 🛠️ Support

Please open an issue or reach out via GitHub Discussions.
