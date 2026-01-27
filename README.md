<img alt="Minimal Illustration Music SoundCloud Banner" src="https://github.com/user-attachments/assets/810ca1a2-d314-4ca6-8c6b-7c641c183097" />

## What is it?

HackRadar is a **Discord Bot** that tracks upcoming hackathons from **7 major platforms**: **MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill**. It fetches data periodically and notifies your Discord server about new events, with support for personalized subscriptions and smart filtering.

### 🌟 Key Highlights
- 🤖 **Fully Automated**: Fetches and notifies every 12 hours without manual intervention
- 🌐 **7 Platform Coverage**: Aggregates hackathons from MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill
- 🎯 **Dual-Level Filtering**: Server-wide preferences + individual user subscriptions with DM alerts
- ⚡ **Interactive Setup**: Rich Discord UI with select menus and buttons for easy configuration
- 🔍 **Powerful Search**: Search, filter by platform, and browse upcoming events on-demand

## 🚀 Features

*   **Multi-Platform Scraping**: Supports **7 major platforms** - MLH, Devpost, Devfolio, DoraHacks, Unstop, Kaggle, and Hack2Skill.
*   **Real-time Notifications**: Automatically posts new hackathons to your Discord server every 12 hours.
*   **Personalized Subscriptions**: Users can subscribe to specific themes (e.g., "AI", "Blockchain", "Web3") and receive personalized DM alerts for matching hackathons.
*   **Pause/Resume Controls**: Administrators can pause and resume server-wide notifications at any time.
*   **Powerful Slash Commands**: Search, filter by platform, check upcoming events, and manage subscriptions directly from Discord.
*   **Rich Embeds**: Beautifully formatted messages with event banners, prize pools, team size, eligibility criteria, and registration links.
*   **Smart Filtering**: Filter hackathons by platforms and themes to receive only relevant updates.
*   **Database**: Uses PostgreSQL to store hackathon data, guild configurations, and user subscriptions.
*   **Dockerized**: Easy deployment with Docker Compose.

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
*   **Title**: Event name with a random fun emoji (🎉, 🚀, 💡, 🔥, 💻, 🏆, etc.).
*   **Core Details**: 
    *   Duration (Start Date - End Date)
    *   Location
    *   Mode (Online/In-person/Hybrid)
    *   Status
*   **Additional Information** (where available from platform APIs):
    *   💰 Prize Pool & Rewards
    *   👥 Team Size
    *   ✅ Eligibility Criteria
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

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/hackathon-bot.git
    cd hackathon-bot
    ```

2.  **Install dependencies**:
    This project uses `uv` for dependency management.
    ```bash
    uv pip install -e .
    ```

3.  **Set up PostgreSQL**:
    Ensure PostgreSQL is running locally and create a database (e.g., `hackradar`).

4.  **Configure Environment**:
    Create a `.env` file with your database credentials and Discord token.

5.  **Initialize Database**:
    ```bash
    python -m backend.init_db
    ```

6.  **Run the Bot**:
    ```bash
    python main.py
    ```

## ⚙️ Environment Variables
 
Refer to [`.env.example`](.env.example) for the complete list of required environment variables.
 
1.  **Copy the example file**:
    ```bash
    cp .env.example .env
    ```
2.  **Update the values** in `.env`:
    *   `DISCORD_TOKEN`: Your bot token.
    *   `POSTGRES_...`: Database credentials for Docker.
    *   `DATABASE_URL`: Connection string (only if running locally).
    *   `KAGGLE_API_TOKEN`: (Optional) Kaggle API token for accessing Kaggle competitions.

## 🏗️ Architecture & How It Works

### Components Overview
HackRadar is built with a modular architecture consisting of several key components:

1. **Discord Bot (`bot.py`)**: 
   - Handles all Discord interactions using discord.py
   - Implements slash commands and interactive UI components (buttons, select menus)
   - Manages background tasks for periodic hackathon fetching (every 12 hours)
   - Sends notifications to configured channels and subscriber DMs

2. **Platform Adapters (`adapters/`)**: 
   - Each adapter is responsible for fetching data from a specific platform
   - Supported platforms:
     - **Devfolio** (`devfolio.py`): Uses GraphQL API
     - **Devpost** (`devpost.py`): Web scraping with BeautifulSoup
     - **Unstop** (`unstop.py`): REST API integration
     - **DoraHacks** (`dorahacks.py`): REST API integration
     - **MLH** (`mlh.py`): Uses MLH's public API
     - **Kaggle** (`kaggle.py`): Kaggle API for competitions
     - **Hack2Skill** (`hack2skill.py`): REST API integration
   - Normalizes data from different sources into a unified `Hackathon` schema

3. **Database Layer (`backend/`)**: 
   - **Models** (`models.py`): SQLAlchemy ORM models for:
     - `HackathonDB`: Stores all hackathon data
     - `GuildConfig`: Stores server-specific preferences (channel, platforms, themes, pause state)
     - `UserSubscription`: Tracks user theme subscriptions for DM alerts
   - **CRUD Operations** (`crud.py`): Database query functions for searching, filtering, and managing data
   - **Schemas** (`schemas.py`): Pydantic models for data validation

4. **Fetch & Store Engine (`fetch_and_store.py`)**: 
   - Orchestrates the data fetching process across all adapters
   - Detects new hackathons by comparing against existing database records
   - Returns only newly added events to trigger notifications

### Workflow

#### Initial Setup
1. Admin runs `/setup` command
2. Bot presents interactive UI to select:
   - Platforms to track (default: all 7 platforms)
   - Themes to filter (AI, Blockchain, Web, Mobile, Data Science, IoT, Cloud, Security)
   - Notification channel
3. Preferences are stored in PostgreSQL `guild_configs` table

#### Automatic Notifications (Every 12 Hours)
1. Background task triggers `fetch_and_store_hackathons()`
2. All adapters fetch latest data from their respective platforms
3. New hackathons are identified and stored in the database
4. For each guild:
   - Check if notifications are paused (skip if paused)
   - Apply platform and theme filters based on guild preferences
   - Send formatted embeds to the configured channel
5. Check user subscriptions:
   - Match new hackathons against subscribed themes
   - Send personalized DMs to subscribed users

#### On-Demand Commands
- `/search`, `/platform`, `/upcoming`: Query the database and return filtered results
- `/subscribe`, `/unsubscribe`: Manage user preferences in the `user_subscriptions` table
- `/pause`, `/resume`: Update the `notifications_paused` flag in `guild_configs`

### Data Filtering

**Server-Level Filtering** (configured via `/setup`):
- **Platform Filter**: Only show hackathons from selected platforms
- **Theme Filter**: Only show hackathons matching selected themes (tags)
- Default: "all" (no filtering)

**User-Level Subscriptions** (via `/subscribe`):
- Users receive DMs when new hackathons match their subscribed themes
- Matching is done by checking if the subscribed theme is a substring of any hackathon tag
- Example: Subscribing to "AI" matches hackathons tagged with "AI", "Generative AI", "AI/ML", etc.

## 🤝 Contributing

Contributions are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.
