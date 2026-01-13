import os
import logging
import json
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
from backend.crud import search_hackathons

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
        """Sync commands when joining a new guild."""
        print(f"Joined new guild: {guild.name} ({guild.id})")
        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to {guild.name}")
        except Exception as e:
            print(f"Failed to sync commands to {guild.name}: {e}")

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data.get("custom_id") == "set_reminder":
                await interaction.response.send_message("🔔 Reminder set! (This feature is coming soon)", ephemeral=True)


client = MyClient(intents=intents)


@client.tree.command(name="hi", description="Say hi")
async def hi(interaction: discord.Interaction):


    welcome_msg = (
        "👋 **Hello there!**\n\n"
        "I'm **HackRadar**, your personal hackathon assistant! 🚀\n"
        "I can help you find the latest hackathons from **Devpost**, **MLH**, **Devfolio**, and more.\n\n"
        "Use `/fetch` to manually check for new hackathons right now!\n"
        "I also run in the background to keep you updated automatically. Happy Hacking! 💻✨"
    )
    await interaction.response.send_message(welcome_msg)


@client.tree.command(name="fetch", description=
"Manually fetch hackathons and send notifications for newly added ones")
async def fetch(interaction: discord.Interaction):
    """Manually trigger hackathon fetching and send notifications."""
    # Defer the response since fetching might take some time
    await interaction.response.defer(thinking=True)
    
    try:
        logging.info(f"Manual fetch triggered by {interaction.user} in guild {interaction.guild_id}")
        
        # Run the fetch
        new_hackathons = fetch_and_store_hackathons()
        
        if not new_hackathons:
            await interaction.followup.send("✅ Fetch completed! No new hackathons found.")
            logging.info("Manual fetch completed: No new hackathons")
            return
        
        # Send summary message
        await interaction.followup.send(
            f"✅ Fetch completed! Found **{len(new_hackathons)}** new hackathon(s). Sending notifications..."
        )
        
        # Send notifications to the current channel
        channel = interaction.channel
        if channel and channel.permissions_for(interaction.guild.me).send_messages:
            await send_hackathon_notifications(client, new_hackathons, target_channel=channel)
            logging.info(f"Manual fetch completed: Sent {len(new_hackathons)} notifications")
        else:
            await interaction.followup.send(
                "⚠️ Fetch completed but I don't have permission to send messages in this channel."
            )
            logging.warning(f"Manual fetch completed but no permission to send in channel {channel.id}")
            
    except Exception as e:
        error_msg = f"❌ Error during fetch: {str(e)}"
        await interaction.followup.send(error_msg)
        logging.error(f"Error in manual fetch command: {e}")


@client.tree.command(name="set_channel", description="Set the channel for hackathon notifications")
@app_commands.describe(channel="The channel to send notifications to")
@app_commands.checks.has_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the preferred channel for hackathon notifications."""
    await interaction.response.defer(thinking=True)
    
    try:
        db = SessionLocal()
        guild_id = str(interaction.guild_id)
        channel_id = str(channel.id)
        
        # Check if config exists
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
        
        if config:
            config.channel_id = channel_id
        else:
            config = GuildConfig(guild_id=guild_id, channel_id=channel_id)
            db.add(config)
            
        db.commit()
        db.close()
        
        await interaction.followup.send(f"✅ Notifications will now be sent to {channel.mention}")
        logging.info(f"Set notification channel for guild {guild_id} to {channel_id}")
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error setting channel: {str(e)}")
        logging.error(f"Error in set_channel command: {e}")

@set_channel.error
async def set_channel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
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
        await send_hackathon_notifications(client, results, target_channel=interaction.channel)
    else:
        # Fallback if channel is not available (e.g. ephemeral context where channel is not accessible)
        # But usually interaction.channel is available.
        # If not, we can iterate and send as followup, but user asked to use the function.
        # Let's try to get channel from interaction.
        pass

def format_hackathon_embed(hackathon):
    """Create a Discord embed for a hackathon notification."""

    # Plain markdown with bold keys and highlighted values
    msg = f"## 🎉 New Hackathon: **{hackathon.title}**\n\n"
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
            label="🚀 Register Now",
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
        for hackathon in new_hackathons:
            try:
                msg, embed, view = format_hackathon_embed(hackathon)
                await target_channel.send(msg, embed=embed, view=view)
                logging.info(f"Sent notification for hackathon '{hackathon.title}' to channel {target_channel.id}")
            except Exception as e:
                logging.error(f"Failed to send hackathon notification to channel {target_channel.id}: {e}")
    else:
        # Send to all guilds (for scheduled task)
        db = SessionLocal()
        
        for guild in bot.guilds:
            channel = None
            
            # 1. Check for configured channel in DB
            try:
                config = db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).first()
                if config:
                    channel = guild.get_channel(int(config.channel_id))
                    if channel and not channel.permissions_for(guild.me).send_messages:
                        logging.warning(f"Configured channel {channel.id} in guild {guild.id} is not writable")
                        channel = None # Fallback to auto-detection
            except Exception as e:
                logging.error(f"Error fetching guild config for {guild.id}: {e}")

            # 2. Fallback: Prefer the system channel if available
            if channel is None:
                if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                    channel = guild.system_channel
            
            # 3. Fallback: first text channel where the bot can send messages
            if channel is None:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break

            if channel is None:
                logging.warning(f"No suitable channel found in guild {guild.id}")
                continue

            # Send notification for each new hackathon
            for hackathon in new_hackathons:
                try:
                    msg, embed, view = format_hackathon_embed(hackathon)
                    await channel.send(msg, embed=embed, view=view)
                    logging.info(f"Sent notification for hackathon '{hackathon.title}' to guild {guild.id}")
                except Exception as e:
                    logging.error(f"Failed to send hackathon notification in guild {guild.id}: {e}")
        
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