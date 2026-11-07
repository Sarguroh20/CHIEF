# CHIEF – Voice-Based Executive Assistant

**CHIEF** is an AI-powered, voice-based executive assistant designed to simplify business workflows through intelligent multi-agent automation.

It enables users to manage employee tasks, monitor progress, generate executive briefings, and schedule meetings using natural-language and voice interactions.

Built for the **WeMakeDevs FLIP THE SWITCH Hackathon**, CHIEF combines AI agents, the Model Context Protocol (MCP), and Google Calendar integration to streamline everyday business operations.

## 🚀 Features

- **Voice-Based Interaction:** Communicate with CHIEF using natural language and voice commands.
- **Intelligent Task Management:** Create, retrieve, filter, and update employee tasks.
- **Task Status Tracking:** Manage task statuses: Created, In Progress, and Completed.
- **Executive Briefing:** Generate management summaries containing task statistics, overdue tasks, today's deadlines, and employee workload.
- **Google Calendar Integration:** Create meetings and retrieve upcoming calendar events.
- **Persistent Database:** Store task information in SQLite and retain records across application restarts.
- **Multi-Agent Architecture:** Delegate operations to specialized agents through a central orchestrator.
- **MCP Integration:** Expose CHIEF capabilities as tools that AI assistants can access through the Model Context Protocol.
- **Notification Management:** Monitor task-related notifications and mark them as read.

## 🧠 Multi-Agent Architecture

CHIEF follows a modular architecture in which specialized agents handle different business operations.

| Component | Responsibility |
|---|---|
| Executive Orchestrator | Routes requests to the appropriate agent |
| Task Agent | Creates, retrieves, filters, and updates tasks |
| Natural Language Task Agent | Interprets user instructions and identifies the required action |
| Calendar Agent | Handles meeting creation and calendar operations |
| Notification Service | Monitors and manages task-related notifications |
| MCP Server | Exposes CHIEF operations as tools for AI assistants |

### How It Works

1. The user provides a voice or natural-language instruction.
2. The Natural Language Task Agent interprets the instruction.
3. The Executive Orchestrator identifies the appropriate operation.
4. The relevant specialized agent executes the operation.
5. CHIEF returns the result to the user and updates the relevant data source.

## 🔗 SWITCH Integration

CHIEF was developed for the **WeMakeDevs SWITCH Hackathon**.

The project uses a Model Context Protocol (MCP) server connected to Codex, allowing an AI assistant to access CHIEF's capabilities through specialized tools.

### MCP Tools

The `chief-tasks` MCP server exposes seven tools:

| Tool | Description |
|---|---|
| `create_task` | Assign a task to an employee |
| `list_tasks` | Retrieve all tasks |
| `update_task_status` | Update an existing task's status |
| `filter_tasks` | Retrieve tasks by status |
| `executive_briefing` | Generate an executive management briefing |
| `create_meeting` | Schedule a meeting in Google Calendar |
| `list_meetings` | Retrieve upcoming calendar meetings |

This integration enables AI-assisted interaction with CHIEF's business workflow operations.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| HTML, CSS, JavaScript | Frontend development |
| SQLite | Persistent database |
| Codex | AI-assisted development and MCP tool interaction |
| Model Context Protocol (MCP) | Agent and tool integration |
| Google Calendar API | Meeting management |
| Git and GitHub | Version control and project hosting |

## 📁 Project Structure

```text
CHIEF/
│
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── calendar_agent.py
│   │   ├── nl_task_agent.py
│   │   ├── orchestrator.py
│   │   └── task_agent.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── google_calendar_service.py
│   │   └── notification_service.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_nl_task_agent.py
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── notification_tools.py
│   │   └── task_tools.py
│   │
│   ├── app.py
│   ├── main.py
│   ├── mcp_server.py
│   └── opencode.json
│
├── frontend/
│   └── index.html
│
├── requirements.txt
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- A Google account for Google Calendar integration
- Google Cloud project with the Google Calendar API enabled

### 1. Clone the repository

```bash
git clone https://github.com/Sarguroh20/CHIEF.git
cd CHIEF
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

### 4. Configure Google Calendar

To enable Google Calendar functionality:

1. Open the Google Cloud Console.
2. Create or select a Google Cloud project.
3. Enable the Google Calendar API.
4. Configure OAuth credentials.
5. Download the OAuth client credentials.
6. Place the credentials file inside the `backend` directory and name it `credentials.json`.
7. Start CHIEF and complete Google authorization through the browser when prompted.

**Security:** Never commit `credentials.json`, `token.json`, API keys, or other private credentials to GitHub.

### 5. Run CHIEF

From the project root:

```bash
cd backend
python app.py
```

The backend server starts at:

```text
http://127.0.0.1:8000
```

Open this address in your browser to access the CHIEF dashboard.

## 💬 Example Voice and Natural-Language Commands

Users can interact with CHIEF using instructions such as:

**Task Management**

- "Assign Rahul the task of submitting the sales report by tomorrow."
- "Show me all tasks."
- "Update Rahul's task to In Progress."
- "Show me all completed tasks."

**Executive Briefing**

- "Give me today's executive briefing."
- "Show me overdue tasks."
- "Show me tasks due today."

**Calendar Management**

- "Schedule a meeting with Rahul tomorrow at 3 PM about the sales review."
- "Show my upcoming meetings."

## 🗄️ Data Persistence

CHIEF uses SQLite for persistent task storage.

- Task records are stored in a local SQLite database.
- Existing task data remains available after application restarts.
- Task operations interact with the persistent database.
- Google Calendar events are managed through the connected Google account.

The local database and private OAuth files are excluded from version control.

## 🔐 Security

- Google OAuth credentials are stored locally.
- Private credentials and tokens are excluded through `.gitignore`.
- Database files are not committed to the public repository.
- Users must configure their own Google Calendar credentials.

## 🎯 Hackathon Information

**Event:** WeMakeDevs SWITCH Hackathon

**Project Name:** CHIEF – Voice-Based Executive Assistant

**Category:** Best Business Workflow

**Objective:** Simplify business operations through voice-based interaction, intelligent task automation, multi-agent coordination, and calendar management.

## 👨‍💻 Repository

**GitHub:** https://github.com/Sarguroh20/CHIEF

---

*CHIEF – Making business workflows smarter, simpler, and more efficient through AI-powered assistance.*
