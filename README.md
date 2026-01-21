<img width="2480" height="520" alt="Minimal Illustration Music SoundCloud Banner" src="https://github.com/user-attachments/assets/810ca1a2-d314-4ca6-8c6b-7c641c183097" />

## What is it?

HackRadar is a **Discord Bot** that tracks upcoming hackathons from major platforms like **MLH, Devpost, Devfolio, DoraHacks, and Unstop**. It fetches data periodically and notifies your Discord server about new events.

## 🚀 Features

*   **Multi-Platform Scraping**: Supports MLH, Devpost, Devfolio, DoraHacks, and Unstop.
*   **Real-time Notifications**: Automatically posts new hackathons to your Discord server every 12 hours.
*   **Personalized Subscriptions**: Users can subscribe to specific themes (e.g., "AI", "Blockchain") and receive DM alerts.
*   **Powerful Slash Commands**: Search, filter by platform, and check upcoming events directly from Discord.
*   **Rich Embeds**: Beautifully formatted messages with banners, prize details, and registration links.
*   **Database**: Uses PostgreSQL to store hackathon data and user subscriptions.
*   **Dockerized**: Easy deployment with Docker Compose.

## 🤖 Commands

| Command | Description | Usage |
| :--- | :--- | :--- |
| `/hi` | Get a warm welcome and introduction to the bot. | `/hi` |
| `/help` | View the full command guide with usage examples. | `/help` |
| `/fetch` | Manually trigger a hackathon fetch update. Notifies the channel and subscribers if new events are found. | `/fetch` |
| `/search` | Search for hackathons by keyword (e.g., "Python", "Web3"). | `/search keyword:AI` |
| `/platform` | Get the latest hackathons from a specific platform. | `/platform name:devpost count:5` |
| `/upcoming` | List hackathons starting in the next X days. | `/upcoming days:14` |
| `/subscribe` | Subscribe to DM notifications for a specific theme. | `/subscribe theme:Blockchain` |
| `/unsubscribe` | Unsubscribe from a theme. | `/unsubscribe theme:Blockchain` |
| `/set_channel` | **(Admin)** Set the default channel for automatic notifications. | `/set_channel channel:#hackathons` |

## 🎨 Notification Format

HackRadar sends visually rich notifications including:
*   **Title**: Event name with a random fun emoji.
*   **Details**: Duration, Location, Mode (Online/In-person), and Status.
*   **Extras**: Prize Pool, Team Size, and Eligibility criteria (where available).
*   **Visuals**: Event banner image.
*   **Actions**:
    *   `🚀 Check Details`: Direct link to the hackathon page.
    *   `🔔 Set Reminder`: (Coming Soon) Personal reminder button.

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

## 🤝 Contributing

Contributions are welcome! Please check the [CONTRIBUTING.md](CONTRIBUTING.md) guide before submitting pull requests.
