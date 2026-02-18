<img alt="Minimal Illustration Music SoundCloud Banner" src="https://github.com/user-attachments/assets/810ca1a2-d314-4ca6-8c6b-7c641c183097" />

## What is it?

HackRadar is a **Discord Bot** that tracks hackathons from **7 platforms** (MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, Hack2Skill) and notifies your server with personalized filtering.

### Key Highlights
- **Fully Automated**: Auto-fetches and notifies every 12 hours
- **7 Platform Coverage**: MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, Hack2Skill
- **Dual-Level Filtering**: Server-wide preferences + personal DM subscriptions
- **Interactive Setup**: Rich Discord UI with menus and buttons
- **Powerful Search**: Search, filter by platform, and browse events on-demand

## 🤖 Commands

### 🔧 Admin Commands (Requires Administrator Permission)
| Command | Description |
| :--- | :--- |
| `/setup` | Configure bot preferences for your server (platforms, themes, notification channel). |
| `/pause` | Pause automatic hackathon notifications for your server. |
| `/resume` | Resume automatic hackathon notifications for your server. |

### 🔍 Discovery Commands
| Command | Description |
| :--- | :--- |
| `/search` | Search for hackathons by keyword (searches titles, tags, and descriptions). |
| `/platform` | Get the latest hackathons from a specific platform. |
| `/upcoming` | List hackathons starting in the next X days. |

### 🔔 Personal Subscription Commands
| Command | Description |
| :--- | :--- |
| `/subscribe` | Subscribe to DM notifications for a specific theme. Get alerted when matching hackathons are posted. |
| `/unsubscribe` | Unsubscribe from a theme's DM notifications. |
| `/subscriptions` | View all your active theme subscriptions. |

### ℹ️ Information Commands
| Command | Description |
| :--- | :--- |
| `/help` | View the full command guide with all available commands and usage examples. |
| `/about` | Learn about HackRadar, view platform statistics, and access support links. |

## 🎨 Notification Format

HackRadar sends visually rich notifications including:
*   **Title**: Event name with a random fun emoji.
*   **Core Details**:
    *   Duration (Start Date - End Date)
    *   Location
    *   Mode (Online/In-person/Hybrid)
    *   Status
*   **Additional Information** (where available from platform APIs):
    *   Prize Pool & Rewards
    *   Team Size
    *   Eligibility Criteria
*   **Visuals**: Event banner image (when available)
*   **Interactive Buttons**:
    *   `🚀 Check Details`: Direct link to the official hackathon registration page

## ⚡ Quick Start (Docker)

1.  **Configure Environment**:
    Copy the example environment file and fill in your details:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` with your Discord token and database credentials.

2.  **Run with Docker Compose**:
    ```bash
    docker compose build
    docker compose up -d
    ```

    The bot will start automatically and begin fetching hackathons.

## 🛠 Local Setup

### Prerequisites
- Python 3.13+ installed
- PostgreSQL installed and running locally
- A Discord Bot Token (see step 2)
- Kaggle API Token (optional, for Kaggle competitions)

### Step-by-Step Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Spartan-71/Discord-Hackathon-Bot.git
    cd Discord-Hackathon-Bot
    ```

2.  **Create a Discord Bot and Get Token**:
    - Go to [Discord Developer Portal](https://discord.com/developers/applications)
    - Click "New Application" and give it a name
    - Go to the "Bot" section and click "Add Bot"
    - Under "Token", click "Reset Token" or "Copy" to get your bot token
    - Enable "Message Content Intent" under "Privileged Gateway Intents"
    - Go to "OAuth2" → "URL Generator", select `bot` and `applications.commands` scopes
    - Copy the generated URL and open it in your browser to invite the bot to your server

3.  **Set up PostgreSQL Database**:
    ```bash
    # Create a new database (example)
    createdb hackradar

    # Or using psql
    psql -U postgres
    CREATE DATABASE hackradar;
    ```

4.  **Install dependencies**:
    This project uses `uv` for dependency management.
    ```bash
    # Install uv if you don't have it
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Install project dependencies
    uv pip install -e .
    ```

5.  **Configure Environment Variables**:
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

    Edit `.env` and configure the following all

    **Required:**
    - `DISCORD_TOKEN`: Your Discord bot token from step 2
    - `DATABASE_URL`: PostgreSQL connection string
    - `KAGGLE_API_TOKEN`: Your Kaggle API token (get it from [Kaggle Account Settings](https://www.kaggle.com/settings))
      - Go to Kaggle → Account → API → Create New Token
      - This enables Kaggle competition tracking

6.  **Initialize Database**:
    ```bash
    python -m backend.init_db
    ```

7.  **Run the Bot**:
    ```bash
    python bot.py
    ```

    You should see a message confirming the bot is online and connected to your Discord server!


## 🏗️ Project Structure

```
Hackathon-Bot/
├── adapters/          # Platform-specific scrapers (MLH, Devpost, etc.)
├── backend/           # Database models, CRUD operations, schemas
├── docs/              # Documentation (privacy policy, terms of service)
├── tests/             # Test suite
├── bot.py             # Main Discord bot application
├── fetch_and_store.py # Scheduled hackathon fetching logic
└── pyproject.toml     # Project dependencies and configuration
```

## 🛠️ Tech Stack

- **Python 3.13+** - Core language
- **discord.py** - Discord bot framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Database
- **BeautifulSoup4** - Web scraping
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **uv** - Fast Python package manager


## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.
