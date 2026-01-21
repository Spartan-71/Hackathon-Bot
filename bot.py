import os
import logging
import json
import random
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from fetch_and_store import run as fetch_and_store_hackathons
# from backend.db import Base, engine
import backend.models
from backend.models import GuildConfig, HackathonDB
from backend.db import SessionLocal
from backend.crud import search_hackathons, get_hackathons_by_platform, get_upcoming_hackathons, subscribe_user, get_all_subscriptions, unsubscribe_user,update_guild_preferences, get_guild_config

load_dotenv()

intents = discord.Intents.default()  # no privileged intents required for slash commands
intents.guilds = True  # needed to see guilds and channels


class MyClient(discord.Client):
    def __init__(self, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)


    async def setup_hook(self):

        # Start the background task once the bot is ready
        if not check_and_notify_hackathons.is_running():
            check_and_notify_hackathons.start(self)

    async def on_ready(self):

        print(f'Bot is in {len(self.guilds)} servers:')
        for guild in self.guilds:
            print(f'- {guild.name} (ID: {guild.id})')
            print(f'  Channels: {len(guild.text_channels)}')
            print(f"Logged on as {self.user}")
        
        # Sync commands after bot is ready - sync to each guild for instant updates
    
        try:
            # Sync to each guild for instant updates (faster than global sync)
            for guild in self.guilds:
                try:
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                    print(f"Cleared guild commands for {guild.name}")
                except Exception as e:
                    print(f"Failed to clear commands for {guild.name}: {e}")
            
            # Also sync globally (takes up to 1 hour but ensures commands work everywhere)
 
            synced_global = await self.tree.sync()

            print(f"Synced {len(synced_global)} commands globally")
        except Exception as e:
            print(f"Error syncing commands: {e}")

    async def on_guild_join(self, guild):
        """Sync commands when joining a new guild and send welcome message."""
        print(f"Joined new guild: {guild.name} ({guild.id})")
        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to {guild.name}")
        except Exception as e:
            print(f"Failed to sync commands to {guild.name}: {e}")

        # Send welcome message
        try:
            target_channel = guild.system_channel
            if not target_channel:
                # Fallback to first text channel if system channel is not available
                target_channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)

            if target_channel and target_channel.permissions_for(guild.me).send_messages:
                embed = discord.Embed(
                    title="🎉 Welcome to HackRadar!",
                    description=(
                        "Thanks for adding me! I'll help your community stay updated on the latest hackathons.\n\n"
                        "**What I can do:**\n"
                        "- Automatic notifications from Devfolio, Devpost, Unstop & more\n"
                        "- Filter by themes (AI, Blockchain, Web3, etc.)\n"
                        "- Track upcoming deadlines and events\n"
                        "- Search hackathons on-demand\n\n"
                    ),
                    color=discord.Color.green()
                )
                 
                # Add example commands
                embed.add_field(
                    name="🔍 Try These Commands",
                    value=(
                        "`/upcoming 7` - Hackathons starting this week\n"
                        "`/search AI` - Find AI-related hackathons\n"
                        "`/help` - See all available commands"
                    ),
                    inline=False
                )
                
                if self.user:
                    embed.set_thumbnail(url=self.user.display_avatar.url)
                
                # Create setup button
                view = WelcomeView()
                
                await target_channel.send(
                    embed=embed,
                    view=view
                )
                logging.info(f"✅ Welcome message sent in {guild.name} (#{target_channel.name})")
        except Exception as e:
            logging.error(f"Failed to send welcome message in {guild.name}: {e}")

    async def on_guild_remove(self, guild):
        """Cleanup data when removed from a guild."""
        print(f"Removed from guild: {guild.name} ({guild.id})")
        try:
            db = SessionLocal()
            # Delete guild config
            db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).delete()
            db.commit()
            db.close()
            logging.info(f"Deleted data for guild {guild.id} after removal")
        except Exception as e:
            logging.error(f"Failed to cleanup data for guild {guild.id}: {e}")

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "set_reminder":
                await interaction.response.send_message("🔔 Reminder set! (This feature is coming soon)", ephemeral=True)


class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Quick Setup", style=discord.ButtonStyle.primary, custom_id="welcome_setup")
    async def setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to use this command.\n"
                "💡 Ask a server admin to run `/setup` or click this button.",
                ephemeral=True
            )
            return
        
        # Execute the setup command logic directly
        embed = discord.Embed(
            title="⚙️ HackRadar Setup",
            description="Please select your preferences below:\n\n"
                        "1. **Platforms**: Choose which platforms to track.\n"
                        "2. **Themes**: Choose which themes to track.\n"
                        "3. **Channel**: Select where to post notifications.\n\n"
                        "Click **Save Preferences** when done.",
            color=discord.Color.blue()
        )
        view = SetupView(str(interaction.guild_id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, guild_id: str):
        super().__init__()
        self.guild_id = guild_id
        self.platforms = []
        self.themes = []
        self.channel = None

    @discord.ui.select(
        placeholder="Select Platforms [Default: All]",
        min_values=0,
        max_values=7,
        options=[
            discord.SelectOption(label="Devfolio", value="devfolio"),
            discord.SelectOption(label="Devpost", value="devpost"),
            discord.SelectOption(label="Unstop", value="unstop"),
            discord.SelectOption(label="DoraHacks", value="dorahacks"),
            discord.SelectOption(label="Hack2Skill",value="hack2skill"),
            discord.SelectOption(label="Kaggle",value="kaggle"),
            discord.SelectOption(label="MLH", value="mlh"),
        ]
    )
    async def select_platforms(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.platforms = select.values
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="Select Themes [Default: All]",
        min_values=0,
        max_values=8,
        options=[
            discord.SelectOption(label="AI/ML", value="ai"),
            discord.SelectOption(label="Blockchain/Web3", value="blockchain"),
            discord.SelectOption(label="Web Development", value="web"),
            discord.SelectOption(label="Mobile App", value="mobile"),
            discord.SelectOption(label="Data Science", value="data"),
            discord.SelectOption(label="IoT", value="iot"),
            discord.SelectOption(label="Cloud", value="cloud"),
            discord.SelectOption(label="Cybersecurity", value="security"),
        ]
    )
    async def select_themes(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.themes = select.values
        await interaction.response.defer()

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Notification Channel"
    )
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.channel = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Save Preferences", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel:
            await interaction.response.send_message("❌ Please select a channel first!", ephemeral=True)
            return

        db = SessionLocal()
        try:
            update_guild_preferences(
                db, 
                self.guild_id, 
                str(self.channel.id), 
                self.platforms, 
                self.themes
            )
            # Create a view with GitHub star button
            github_view = discord.ui.View()
            github_view.add_item(discord.ui.Button(
                label="⭐ Star on GitHub",
                url="https://github.com/Spartan-71/Discord-Hackathon-Bot",
                style=discord.ButtonStyle.link
            ))
            
            # Create success embed
            success_embed = discord.Embed(
                title="✅ Setup Complete!",
                description=(
                    "Your preferences have been saved successfully!\n\n"
                    f"**Notification Channel:** {self.channel.mention}\n"
                    f"**Platforms:** {', '.join(self.platforms) if self.platforms else 'All (Default)'}\n"
                    f"**Themes:** {', '.join(self.themes) if self.themes else 'All (Default)'}\n\n"
                    "🎉 You'll start receiving hackathon notifications soon.\n"
                ),
                color=discord.Color.green()
            )
                        
            await interaction.response.send_message(
                embed=success_embed,
                view=github_view,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error saving preferences: {str(e)}", ephemeral=True)
        finally:
            db.close()

client = MyClient(intents=intents)



@client.tree.command(name="setup", description="Configure bot preferences for this server")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    """Configure bot preferences."""
    embed = discord.Embed(
        title="⚙️ HackRadar Setup",
        description="Please select your preferences below:\n\n"
                    "1. **Platforms**: Choose which platforms to track.\n"
                    "2. **Themes**: Choose which themes to track.\n"
                    "3. **Channel**: Select where to post notifications.\n\n"
                    "💡 *Leave empty to receive all notifications.*\n\n"
                    "Click **Save Preferences** when done.",
        color=discord.Color.blue()
    )
    view = SetupView(str(interaction.guild_id))
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@setup.error
async def setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)


@client.tree.command(name="search", description="Search hackathons by keywords.")
@app_commands.describe(keyword="Search term (e.g.,AI, Blockchain, Data Science)")
async def search(interaction: discord.Interaction, keyword: str):
    """Search hackathons"""
    await interaction.response.defer(thinking=True)
    
    db = SessionLocal()
    try:
        logging.info(f"Search query: {keyword} by user {interaction.user.id}")
        results = search_hackathons(db, keyword)
    finally:
        db.close()
    
    if not results:
        await interaction.followup.send(
            f"❌ No hackathons found for **{keyword}**",
            ephemeral=True
        )
        return
    
    await interaction.followup.send(f"🔍 Found **{len(results)}** hackathon(s) for **{keyword}**:")
    
    # Use the shared notification function
    if interaction.channel:
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if permissions.send_messages and permissions.embed_links:
            await send_hackathon_notifications(client, results, target_channel=interaction.channel)
        else:
            await interaction.followup.send(
                "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                ephemeral=True
            )
    else:
        # Fallback if channel is not available
        pass


@client.tree.command(name="platform", description="Get latest hackathons from a specific platform")
@app_commands.describe(name="Platform name (e.g., unstop, devfolio)", count="Number of results to return (default 3)")
async def platform(interaction: discord.Interaction, name: str, count: int = 3):
    """Get hackathons from a specific platform"""
    await interaction.response.defer(thinking=True)
    
    db = SessionLocal()
    try:
        logging.info(f"Platform query: {name} by user {interaction.user.id}")
        results = get_hackathons_by_platform(db, name, count)
    finally:
        db.close()
    
    if not results:
        await interaction.followup.send(
            f"❌ No hackathons found for platform **{name}**",
            ephemeral=True
        )
        return
    
    await interaction.followup.send(f"🔍 Found **{len(results)}** hackathon(s) from **{name}**:")
    
    # Use the shared notification function
    if interaction.channel:
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if permissions.send_messages and permissions.embed_links:
            await send_hackathon_notifications(client, results, target_channel=interaction.channel)
        else:
            await interaction.followup.send(
                "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                ephemeral=True
            )
    else:
        pass


@client.tree.command(name="upcoming", description="Get hackathons starting in the next X days")
@app_commands.describe(days="Number of days to look ahead (default 7)")
async def upcoming(interaction: discord.Interaction, days: int = 7):
    """Get hackathons starting in the next X days"""
    await interaction.response.defer(thinking=True)
    
    db = SessionLocal()
    try:
        results = get_upcoming_hackathons(db, days)
    finally:
        db.close()
    
    if not results:
        await interaction.followup.send(
            f"❌ No upcoming hackathons found in the next **{days}** days.",
            ephemeral=True
        )
        return
    
    await interaction.followup.send(f"📅 Found **{len(results)}** upcoming hackathon(s) in the next **{days}** days:")
    
    # Use the shared notification function
    if interaction.channel:
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if permissions.send_messages and permissions.embed_links:
            await send_hackathon_notifications(client, results, target_channel=interaction.channel)
        else:
            await interaction.followup.send(
                "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                ephemeral=True
            )
    else:
        pass


@client.tree.command(name="subscribe", description="Subscribe to hackathon notifications for a specific theme")
@app_commands.describe(theme="The theme to subscribe to (e.g., AI, Blockchain)")
async def subscribe(interaction: discord.Interaction, theme: str):
    """Subscribe to a theme."""
    await interaction.response.defer(ephemeral=True)
    
    db = SessionLocal()
    try:
        sub, is_new = subscribe_user(db, interaction.user.id, theme)
        if is_new:
            await interaction.followup.send(f"✅ You have successfully subscribed to **{theme}** updates!")
        else:
            await interaction.followup.send(f"ℹ️ You are already subscribed to **{theme}**.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error subscribing: {str(e)}")
        logging.error(f"Error in subscribe command: {e}")
    finally:
        db.close()


@client.tree.command(name="unsubscribe", description="Unsubscribe from hackathon notifications for a specific theme")
@app_commands.describe(theme="The theme to unsubscribe from")
async def unsubscribe(interaction: discord.Interaction, theme: str):
    """Unsubscribe from a theme."""
    await interaction.response.defer(ephemeral=True)
    
    db = SessionLocal()
    try:
        removed = unsubscribe_user(db, interaction.user.id, theme)
        if removed:
            await interaction.followup.send(f"✅ You have successfully unsubscribed from **{theme}** updates.")
        else:
            await interaction.followup.send(f"ℹ️ You were not subscribed to **{theme}**.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error unsubscribing: {str(e)}")
        logging.error(f"Error in unsubscribe command: {e}")
    finally:
        db.close()


@client.tree.command(name="help", description="Show the command guide and usage examples")
async def help(interaction: discord.Interaction):
    """Show the command guide."""
    embed = discord.Embed(
        title="🛠️ HackRadar Command Guide",
        description="Here are the commands you can use to interact with HackRadar:",
        color=discord.Color.blue()
    )
    
    commands_info = [
        ("👋 /hi", "Say hello to the bot and get a quick intro."),
        ("🔄 /fetch", "Manually check for new hackathons immediately."),
        ("🔍 /search [keyword]", "Search for hackathons by topic (e.g., `/search AI`)."),
        ("🌐 /platform [name] [count]", "Get hackathons from a specific platform (e.g., `/platform devfolio`)."),
        ("📅 /upcoming [days]", "See hackathons starting in the next X days (e.g., `/upcoming 14`)."),
        ("🔔 /subscribe [theme]", "Get DM alerts for a specific theme (e.g., `/subscribe blockchain`)."),
        ("🔕 /unsubscribe [theme]", "Stop receiving DM alerts for a theme."),
        ("⚙️ /set_channel [channel]", "(Admin only) Set the channel for automatic notifications.")
    ]

    for cmd, desc in commands_info:
        embed.add_field(name=cmd, value=desc, inline=False)

    await interaction.response.send_message(embed=embed)


def format_hackathon_embed(hackathon):
    """Create a Discord embed for a hackathon notification."""

    # Plain markdown with bold keys and highlighted values
    emojis = ["🎉", "🚀", "💡", "🔥", "💻", "🏆", "🌟", "⚡", "🔮", "🛠️"]
    random_emoji = random.choice(emojis)
    msg = f"# {random_emoji} **{hackathon.title}**\n\n"
    msg += f"---\n"
    msg += f"**Duration:** {hackathon.start_date.strftime('%B %d')} - {hackathon.end_date.strftime('%B %d, %Y')}\n"
    msg += f"**Location:** {hackathon.location}\n"
    msg += f"**Mode:** {hackathon.mode}\n"
    msg += f"**Status:** {hackathon.status}\n"
    if hackathon.prize_pool:
        if "\n" in hackathon.prize_pool or hackathon.prize_pool.startswith("-"):
            msg += f"**Prizes:**\n{hackathon.prize_pool}\n"
        else:
            msg += f"**Prizes:** {hackathon.prize_pool}\n"
    if hackathon.team_size:
        msg += f"**Team Size:** {hackathon.team_size}\n"
    if hackathon.eligibility:
        msg += f"**Eligibility:** {hackathon.eligibility}\n"
    msg += f"---\n"

    embed = None
    if hackathon.banner_url:
        embed = discord.Embed()
        embed.set_image(url=hackathon.banner_url)

    view = discord.ui.View()

    # Register button
    if hackathon.url:
        view.add_item(discord.ui.Button(
            label="🚀 Check Details",
            url=hackathon.url,
            style=discord.ButtonStyle.link
        ))

    # Reminder button
    view.add_item(discord.ui.Button(
        label="🔔 Set Reminder",
        style=discord.ButtonStyle.primary,
        custom_id="set_reminder"
    ))

    return msg, embed, view


async def send_hackathon_notifications(bot: MyClient, new_hackathons, target_channel=None):
    """
    Send hackathon notifications to channels.
    If target_channel is provided, send there. Otherwise, send to all guilds using configured or default channels.
    """
    if not new_hackathons:
        return
    
    if target_channel:
        # Send to specific channel (for manual fetch command)
        # Check permissions again to be safe
        permissions = target_channel.permissions_for(target_channel.guild.me)
        if not (permissions.send_messages and permissions.embed_links):
            logging.warning(f"Missing permissions in target channel {target_channel.id}. Skipping notifications.")
            return

        for hackathon in new_hackathons:
            try:
                msg, embed, view = format_hackathon_embed(hackathon)
                await target_channel.send(msg, embed=embed, view=view)
                logging.info(f"Sent notification for hackathon '{hackathon.title}' to channel {target_channel.id}")
            except discord.Forbidden:
                logging.error(f"403 Forbidden when sending to channel {target_channel.id}. Check permissions.")
            except Exception as e:
                logging.error(f"Failed to send hackathon notification to channel {target_channel.id}: {e}")
    else:
        # Send to all guilds (for scheduled task)
        db = SessionLocal()
        
        for guild in bot.guilds:
            channel = None
            platforms = ["all"]
            themes = ["all"]
            
            # 1. Check for configured channel in DB
            try:
                config = db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).first()
                if config:
                    channel = guild.get_channel(int(config.channel_id))
                    if channel and not channel.permissions_for(guild.me).send_messages:
                        logging.warning(f"Configured channel {channel.id} in guild {guild.id} is not writable")
                        channel = None
                    
                    if config.subscribed_platforms:
                        platforms = config.subscribed_platforms.split(",")
                    if config.subscribed_themes:
                        themes = config.subscribed_themes.split(",")
            except Exception as e:
                logging.error(f"Error fetching guild config for {guild.id}: {e}")

            if channel is None:
                logging.warning(f"No configured notification channel found for guild {guild.id}. Skipping.")
                continue

            # Send notification for each new hackathon
            for hackathon in new_hackathons:
                # Filter by platform
                if "all" not in platforms:
                    if not any(p.lower() in hackathon.source.lower() for p in platforms):
                        continue
                
                # Filter by theme
                if "all" not in themes:
                    hack_tags = [t.lower() for t in hackathon.tags] if hackathon.tags else []
                    # Check if any subscribed theme matches any hackathon tag
                    # Using simple substring match
                    match = False
                    for theme in themes:
                        theme_lower = theme.lower()
                        for tag in hack_tags:
                            if theme_lower in tag:
                                match = True
                                break
                        if match:
                            break
                    
                    if not match:
                        continue

                try:
                    msg, embed, view = format_hackathon_embed(hackathon)
                    await channel.send(msg, embed=embed, view=view)
                    logging.info(f"Sent notification for hackathon '{hackathon.title}' to guild {guild.id}")
                except Exception as e:
                    logging.error(f"Failed to send hackathon notification in guild {guild.id}: {e}")
        
        db.close()


async def notify_subscribers(bot: MyClient, new_hackathons):
    """
    Check new hackathons against user subscriptions and send DMs.
    """
    if not new_hackathons:
        return

    db = SessionLocal()
    try:
        subscriptions = get_all_subscriptions(db)
        if not subscriptions:
            return

        # Map: user_id -> list of hackathons to notify
        user_notifications = {}

        for hackathon in new_hackathons:
            # Hackathon tags are list of strings in Pydantic model
            hack_tags = [t.lower() for t in hackathon.tags] if hackathon.tags else []
            
            # Also check title or description if needed, but sticking to tags/themes as requested
            # User might subscribe to "AI", we check if "ai" is in tags.
            
            for sub in subscriptions:
                # Simple substring match or exact match? 
                # User said "subscribe to a particular theme".
                # If user subscribes to "AI", and tag is "Generative AI", should it match?
                # Probably yes. ilike in DB usually does partial match if we used %%.
                # Here we are doing in-memory check.
                # Let's do: if sub.theme.lower() is in any of the tags (substring match within tags)
                
                theme_lower = sub.theme.lower()
                is_match = False
                for tag in hack_tags:
                    if theme_lower in tag:
                        is_match = True
                        break
                
                if is_match:
                    if sub.user_id not in user_notifications:
                        user_notifications[sub.user_id] = []
                    # Avoid duplicates if multiple themes match same hackathon
                    if hackathon not in user_notifications[sub.user_id]:
                        user_notifications[sub.user_id].append(hackathon)
        
        # Send DMs
        for user_id, hacks in user_notifications.items():
            try:
                user = await bot.fetch_user(user_id)
                if user:
                    for hack in hacks:
                        msg, embed, view = format_hackathon_embed(hack)
                        await user.send(f"🔔 **New Hackathon Alert!** (Matches your subscription)\n", embed=embed, view=view)
                        logging.info(f"Sent DM notification for '{hack.title}' to user {user_id}")
            except Exception as e:
                logging.error(f"Failed to DM user {user_id}: {e}")

    finally:
        db.close()



@tasks.loop(hours=12)  # Run every 12 hours (adjust as needed: seconds=30, minutes=5, hours=12, etc.)
async def check_and_notify_hackathons(bot: MyClient):
    """Background task that fetches hackathons and sends notifications for newly added ones."""
    if not bot.guilds:
        logging.warning("Bot is not in any guilds, skipping hackathon check")
        return

    try:
        logging.info("Starting hackathon fetch and notification check")
        new_hackathons = fetch_and_store_hackathons()
        
        if not new_hackathons:
            logging.info("No new hackathons found")
            return
        
        logging.info(f"Found {len(new_hackathons)} new hackathons, sending notifications")
        
        # Send notifications to all guilds
        await send_hackathon_notifications(bot, new_hackathons)

        # Notify subscribers via DM
        await notify_subscribers(bot, new_hackathons)

        
        logging.info("Completed hackathon notifications")
        
    except Exception as e:
        logging.error(f"Error in check_and_notify_hackathons task: {e}")


@check_and_notify_hackathons.before_loop
async def before_check_and_notify():
    """Wait until the bot is ready before starting the task."""
    await client.wait_until_ready()


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment")

client.run(token)