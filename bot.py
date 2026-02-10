import os
import logging
import random

import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

from fetch_and_store import run as fetch_and_store_hackathons
from backend.models import GuildConfig
from backend.db import SessionLocal
from backend.crud import (
    search_hackathons,
    get_hackathons_by_platform,
    get_upcoming_hackathons,
    subscribe_user,
    get_all_subscriptions,
    get_user_subscriptions,
    unsubscribe_user,
    update_guild_preferences,
    pause_notifications,
    resume_notifications,
)

# 1. Configuration & Logging
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

intents = discord.Intents.default()
intents.guilds = True  # needed to see guilds and channels

# 2. Helper Functions (Basic)


def format_hackathon_embed(hackathon):
    """Create a Discord embed for a hackathon notification."""
    emojis = ["🎉", "🚀", "💡", "🔥", "💻", "🏆", "🌟", "⚡", "🔮", "🛠️"]
    random_emoji = random.choice(emojis)
    msg = f"# {random_emoji} **{hackathon.title}**\n\n"
    msg += "---\n"
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
    msg += "---\n"

    embed = None
    if hackathon.banner_url:
        embed = discord.Embed()
        embed.set_image(url=hackathon.banner_url)

    view = discord.ui.View()

    # Register button
    if hackathon.url:
        view.add_item(
            discord.ui.Button(
                label="🚀 Check Details", url=hackathon.url, style=discord.ButtonStyle.primary
            )
        )

    return msg, embed, view


# 3. UI Classes (Views & Paginators)


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
            discord.SelectOption(label="Hack2Skill", value="hack2skill"),
            discord.SelectOption(label="Kaggle", value="kaggle"),
            discord.SelectOption(label="MLH", value="mlh"),
        ],
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
        ],
    )
    async def select_themes(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.themes = select.values
        await interaction.response.defer()

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select Notification Channel",
    )
    async def select_channel(
        self, interaction: discord.Interaction, select: discord.ui.ChannelSelect
    ):
        self.channel = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="Save Preferences", style=discord.ButtonStyle.green)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.channel:
            await interaction.response.send_message(
                "❌ Please select a channel first!", ephemeral=True
            )
            return

        db = SessionLocal()
        try:
            update_guild_preferences(
                db, self.guild_id, str(self.channel.id), self.platforms, self.themes
            )

            github_view = discord.ui.View()
            github_view.add_item(
                discord.ui.Button(
                    label="⭐ Star on GitHub",
                    url="https://github.com/Spartan-71/Discord-Hackathon-Bot",
                    style=discord.ButtonStyle.link,
                )
            )

            success_embed = discord.Embed(
                title="✅ Setup Complete!",
                description=(
                    "Your preferences have been saved successfully!\n\n"
                    f"**Notification Channel:** {self.channel.mention}\n"
                    f"**Platforms:** {', '.join(self.platforms) if self.platforms else 'All (Default)'}\n"
                    f"**Themes:** {', '.join(self.themes) if self.themes else 'All (Default)'}\n\n"
                    "🎉 You'll start receiving hackathon notifications soon.\n"
                ),
                color=discord.Color.green(),
            )

            await interaction.response.send_message(
                embed=success_embed, view=github_view, ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error saving preferences: {str(e)}", ephemeral=True
            )
        finally:
            db.close()


class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="⚙️ Quick Setup", style=discord.ButtonStyle.primary, custom_id="welcome_setup"
    )
    async def setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to use this command.\n"
                "💡 Ask a server admin to run `/setup` or click this button.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="⚙️ HackRadar Setup",
            description="Please select your preferences below:\n\n"
            "1. **Platforms**: Choose which platforms to track.\n"
            "2. **Themes**: Choose which themes to track.\n"
            "3. **Channel**: Select where to post notifications.\n\n"
            "Click **Save Preferences** when done.",
            color=discord.Color.blue(),
        )
        view = SetupView(str(interaction.guild_id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HackathonPaginator(discord.ui.View):
    """Paginator for displaying hackathons with Previous/Next buttons."""

    def __init__(self, hackathons, context_type="manual"):
        super().__init__(timeout=600)
        self.hackathons = hackathons
        self.context_type = context_type
        self.current_index = 0
        self.max_index = len(hackathons) - 1

        if context_type == "scheduled":
            self.timeout = 3600

        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index == self.max_index

    def add_action_buttons(self, view_buttons):
        self.clear_items()
        if view_buttons:
            for item in view_buttons.children:
                item.row = 0
                self.add_item(item)

        self.previous_button.row = 1
        self.next_button.row = 1
        self.add_item(self.previous_button)
        self.add_item(self.next_button)

    def get_current_hackathon(self):
        return self.hackathons[self.current_index]

    def create_embed(self):
        hackathon = self.get_current_hackathon()
        msg, embed, view = format_hackathon_embed(hackathon)

        if embed:
            current_footer = embed.footer.text if embed.footer else ""
            new_footer = f"📄 {self.current_index + 1}/{len(self.hackathons)}"
            if current_footer:
                new_footer += f" | {current_footer}"
            embed.set_footer(text=new_footer)

        return msg, embed, view

    @discord.ui.button(
        label="◀️ Previous", style=discord.ButtonStyle.gray, custom_id="prev_hack", row=1
    )
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()
            await self._update_message(interaction)
        else:
            await interaction.response.send_message(
                "⚠️ You're already at the first hackathon!", ephemeral=True
            )

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray, custom_id="next_hack", row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < self.max_index:
            self.current_index += 1
            self.update_buttons()
            await self._update_message(interaction)
        else:
            await interaction.response.send_message(
                "⚠️ You're already at the last hackathon!", ephemeral=True
            )

    async def _update_message(self, interaction: discord.Interaction):
        msg, embed, view_buttons = self.create_embed()
        self.add_action_buttons(view_buttons)

        try:
            await interaction.response.edit_message(
                content=msg
                if msg
                else f"📖 Hackathon {self.current_index + 1}/{len(self.hackathons)}:",
                embed=embed,
                view=self,
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "⚠️ Message was deleted. Please run the command again.", ephemeral=True
            )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# 4. Notification Helper Functions


async def send_standard_paginated_notification(channel, hackathons):
    if len(hackathons) == 1:
        hackathon = hackathons[0]
        msg, embed, view = format_hackathon_embed(hackathon)
        if embed:
            await channel.send(content=msg, embed=embed, view=view)
        else:
            await channel.send(content=msg, view=view)
    else:
        paginator = HackathonPaginator(hackathons, context_type="manual")
        msg, embed, view_buttons = paginator.create_embed()
        paginator.add_action_buttons(view_buttons)

        await channel.send(
            content=f"📅 Found **{len(hackathons)}** hackathon(s). Use buttons to navigate:\n\n{msg}",
            embed=embed,
            view=paginator,
        )


async def send_scheduled_notification_with_pagination(channel, hackathons):
    summary_embed = discord.Embed(
        title="🚀 New Hackathons Posted!",
        description=f"**{len(hackathons)}** new hackathon(s) have been posted. Click the buttons below to view details.",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    summary_text = ""
    for i, hack in enumerate(hackathons[:10], 1):
        title = hack.title if len(hack.title) <= 50 else hack.title[:47] + "..."
        summary_text += f"**{i}.** [{title}]({hack.url}) - *{hack.source}*\n"

    if len(hackathons) > 10:
        summary_text += f"\n*...and {len(hackathons) - 10} more. Use buttons below to view all.*"

    summary_embed.add_field(name="📋 Hackathons", value=summary_text, inline=False)
    summary_embed.set_footer(text="💡 Use the buttons below to navigate through details")

    paginator = HackathonPaginator(hackathons, context_type="scheduled")
    msg, embed, view_buttons = paginator.create_embed()
    paginator.add_action_buttons(view_buttons)

    await channel.send(embed=summary_embed)
    await channel.send(
        content=f"📖 **Detailed View** (1/{len(hackathons)}):", embed=embed, view=paginator
    )


async def send_paginated_hackathons(channel, hackathons, context_type="scheduled"):
    if not hackathons:
        return

    if context_type == "scheduled" and len(hackathons) > 1:
        await send_scheduled_notification_with_pagination(channel, hackathons)
    else:
        await send_standard_paginated_notification(channel, hackathons)


async def send_hackathon_notifications(bot, new_hackathons, target_channel=None):
    if not new_hackathons:
        return

    if target_channel:
        permissions = target_channel.permissions_for(target_channel.guild.me)
        if not (permissions.send_messages and permissions.embed_links):
            logging.warning(
                f"Missing permissions in target channel {target_channel.id}. Skipping notifications."
            )
            return

        try:
            await send_paginated_hackathons(
                channel=target_channel, hackathons=new_hackathons, context_type="manual_fetch"
            )
            logging.info(
                f"Sent {len(new_hackathons)} hackathons to channel {target_channel.id} with pagination"
            )
        except discord.Forbidden:
            logging.error(
                f"403 Forbidden when sending to channel {target_channel.id}. Check permissions."
            )
        except Exception as e:
            logging.error(
                f"Failed to send hackathon notifications to channel {target_channel.id}: {e}"
            )
    else:
        db = SessionLocal()
        try:
            for guild in bot.guilds:
                channel = None
                platforms = ["all"]
                themes = ["all"]

                try:
                    config = (
                        db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).first()
                    )
                    if config:
                        if config.notifications_paused == "true":
                            logging.info(
                                f"Notifications are paused for guild {guild.id}. Skipping."
                            )
                            continue

                        channel = guild.get_channel(int(config.channel_id))
                        if channel and not channel.permissions_for(guild.me).send_messages:
                            logging.warning(
                                f"Configured channel {channel.id} in guild {guild.id} is not writable"
                            )
                            channel = None

                        if config.subscribed_platforms:
                            platforms = config.subscribed_platforms.split(",")
                        if config.subscribed_themes:
                            themes = config.subscribed_themes.split(",")
                except Exception as e:
                    logging.error(f"Error fetching guild config for {guild.id}: {e}")

                if channel is None:
                    logging.warning(
                        f"No configured notification channel found for guild {guild.id}. Skipping."
                    )
                    continue

                filtered_hackathons = []
                for hackathon in new_hackathons:
                    if "all" not in platforms:
                        if not any(p.lower() in hackathon.source.lower() for p in platforms):
                            continue

                    if "all" not in themes:
                        hack_tags = [t.lower() for t in hackathon.tags] if hackathon.tags else []
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

                    filtered_hackathons.append(hackathon)

                if filtered_hackathons:
                    try:
                        await send_paginated_hackathons(
                            channel=channel,
                            hackathons=filtered_hackathons,
                            context_type="scheduled",
                        )
                        logging.info(
                            f"Sent {len(filtered_hackathons)} hackathons to guild {guild.id} with pagination"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to send hackathon notifications in guild {guild.id}: {e}"
                        )
                else:
                    logging.info(f"No matching hackathons for guild {guild.id} after filtering")
        finally:
            db.close()


async def notify_subscribers(bot, new_hackathons):
    if not new_hackathons:
        return

    db = SessionLocal()
    try:
        subscriptions = get_all_subscriptions(db)
        if not subscriptions:
            return

        user_notifications = {}
        for hackathon in new_hackathons:
            hack_tags = [t.lower() for t in hackathon.tags] if hackathon.tags else []
            for sub in subscriptions:
                theme_lower = sub.theme.lower()
                is_match = False
                for tag in hack_tags:
                    if theme_lower in tag:
                        is_match = True
                        break

                if is_match:
                    if sub.user_id not in user_notifications:
                        user_notifications[sub.user_id] = []
                    if hackathon not in user_notifications[sub.user_id]:
                        user_notifications[sub.user_id].append(hackathon)

        for user_id, hacks in user_notifications.items():
            try:
                user = await bot.fetch_user(user_id)
                if user:
                    for hack in hacks:
                        msg, embed, view = format_hackathon_embed(hack)
                        alert_msg = (
                            f"🔔 **New Hackathon Alert!** (Matches your subscription)\n\n{msg}"
                        )
                        if embed:
                            await user.send(content=alert_msg, embed=embed, view=view)
                        else:
                            await user.send(content=alert_msg, view=view)
                        logging.info(f"Sent DM notification for '{hack.title}' to user {user_id}")
            except Exception as e:
                logging.error(f"Failed to DM user {user_id}: {e}")
    finally:
        db.close()


# 5. Main Client Class


class MyClient(discord.Client):
    def __init__(self, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if not check_and_notify_hackathons.is_running():
            check_and_notify_hackathons.start(self)

    async def on_ready(self):
        logging.info(f"Logged on as {self.user}")
        logging.info(f"Bot is in {len(self.guilds)} servers:")
        for guild in self.guilds:
            logging.info(f"- {guild.name} (ID: {guild.id}) members: {guild.member_count}")
            logging.info(f"  Channels: {len(guild.text_channels)}")

        try:
            for guild in self.guilds:
                try:
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                except Exception as e:
                    logging.error(f"Failed to clear guild commands for {guild.name}: {e}")

            synced_global = await self.tree.sync()
            logging.info(f"Synced {len(synced_global)} commands globally")
            logging.info("Commands are now available in both servers and DMs!")
        except Exception as e:
            logging.error(f"Error syncing commands: {e}")

    async def on_guild_join(self, guild):
        logging.info(f"Joined new guild: {guild.name} ({guild.id})")
        logging.info("Commands are already available globally (no guild-specific sync needed)")

        try:
            target_channel = guild.system_channel
            if not target_channel:
                target_channel = next(
                    (
                        ch
                        for ch in guild.text_channels
                        if ch.permissions_for(guild.me).send_messages
                    ),
                    None,
                )

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
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="🔍 Try These Commands",
                    value=(
                        "`/upcoming 7` - Hackathons starting this week\n"
                        "`/search AI` - Find AI-related hackathons\n"
                        "`/help` - See all available commands"
                    ),
                    inline=False,
                )
                if self.user:
                    embed.set_thumbnail(url=self.user.display_avatar.url)

                view = WelcomeView()
                await target_channel.send(embed=embed, view=view)
                logging.info(f"✅ Welcome message sent in {guild.name} (#{target_channel.name})")
        except Exception as e:
            logging.error(f"Failed to send welcome message in {guild.name}: {e}")

    async def on_guild_remove(self, guild):
        logging.info(f"Removed from guild: {guild.name} ({guild.id})")
        try:
            db = SessionLocal()
            db.query(GuildConfig).filter(GuildConfig.guild_id == str(guild.id)).delete()
            db.commit()
            db.close()
            logging.info(f"Deleted data for guild {guild.id} after removal")
        except Exception as e:
            logging.error(f"Failed to cleanup data for guild {guild.id}: {e}")


client = MyClient(intents=intents)

# 6. Slash Commands


@client.tree.command(name="setup", description="Configure bot preferences for this server")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ HackRadar Setup",
        description="Please select your preferences below:\n\n"
        "1. **Platforms**: Choose which platforms to track.\n"
        "2. **Themes**: Choose which themes to track.\n"
        "3. **Channel**: Select where to post notifications.\n\n"
        "💡 *Leave empty to receive all notifications.*\n\n"
        "Click **Save Preferences** when done.",
        color=discord.Color.blue(),
    )
    view = SetupView(str(interaction.guild_id))
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@setup.error
async def setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need Administrator permissions to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", ephemeral=True
        )


@client.tree.command(name="search", description="Search hackathons by keywords.")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(keyword="Search term (e.g.,AI, Blockchain, Data Science)")
async def search(interaction: discord.Interaction, keyword: str):
    await interaction.response.defer(thinking=True)
    db = SessionLocal()
    try:
        logging.info(f"Search query: {keyword} by user {interaction.user.id}")
        results = search_hackathons(db, keyword)
    except Exception as e:
        logging.error(f"Error searching hackathons: {e}")
        await interaction.followup.send(
            "❌ An error occurred while searching the database. Please try again later.",
            ephemeral=True,
        )
        return
    finally:
        db.close()

    if not results:
        await interaction.followup.send(f"❌ No hackathons found for **{keyword}**", ephemeral=True)
        return

    if interaction.guild:
        if not interaction.guild.me:
            await interaction.followup.send(
                "⚠️ **I'm not installed in this server!**\n\n"
                "You have two options:\n"
                "1️⃣ **Use me in DMs**: Send me a direct message and use this command there\n"
                "2️⃣ **Add me to this server**: Ask a server admin to invite me\n\n"
                "💡 *Tip: All search commands work perfectly in DMs!*",
                ephemeral=True,
            )
            return

        if interaction.channel:
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if permissions.send_messages and permissions.embed_links:
                try:
                    await interaction.followup.send(
                        f"🔍 Found **{len(results)}** hackathon(s) for **{keyword}**:"
                    )
                    await send_hackathon_notifications(
                        client, results, target_channel=interaction.channel
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "⚠️ **Permission Error**: I don't have permission to send messages in this channel.",
                        ephemeral=True,
                    )
                except Exception as e:
                    logging.error(f"Error sending hackathons to channel: {e}")
                    await interaction.followup.send(
                        "⚠️ An error occurred while sending the results.", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                "⚠️ Unable to determine the channel context.", ephemeral=True
            )
    else:
        logging.info(
            f"Sending {len(results)} search results to user {interaction.user.id} via DM with pagination"
        )
        try:
            paginator = HackathonPaginator(results, context_type="dm")
            msg, embed, view_buttons = paginator.create_embed()
            paginator.add_action_buttons(view_buttons)
            await interaction.followup.send(
                content=f"🔍 Found **{len(results)}** hackathon(s) for **{keyword}**:\n\n{msg}",
                embed=embed,
                view=paginator,
            )
            logging.info(f"Sent paginated search results to user {interaction.user.id}")
        except Exception as e:
            logging.error(f"Failed to send paginated search results: {e}")
            await interaction.followup.send(
                f"⚠️ Error displaying hackathons. Found {len(results)} results but couldn't display them properly.",
                ephemeral=True,
            )


async def platform_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete for platform names."""
    platforms = [
        "devfolio",
        "devpost",
        "unstop",
        "mlh",
        "dorahacks",
        "hack2skill",
        "kaggle",
    ]

    # Filter platforms based on what user is typing
    return [
        app_commands.Choice(name=platform.title(), value=platform)
        for platform in platforms
        if current.lower() in platform.lower()
    ]


@client.tree.command(
    name="platform", description="Get upcoming hackathons from a specific platform"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(name="Select a platform", count="Number of results to return (default 3)")
@app_commands.autocomplete(name=platform_autocomplete)
async def platform(interaction: discord.Interaction, name: str, count: int = 3):
    await interaction.response.defer(thinking=True)
    db = SessionLocal()
    try:
        logging.info(f"Platform query: {name} by user {interaction.user.id}")
        results = get_hackathons_by_platform(db, name, count)
    except Exception as e:
        logging.error(f"Error fetching hackathons by platform: {e}")
        await interaction.followup.send(
            "❌ An error occurred while fetching hackathons. Please try again later.",
            ephemeral=True,
        )
        return
    finally:
        db.close()

    if not results:
        await interaction.followup.send(
            f"❌ No upcoming hackathons found for platform **{name}**", ephemeral=True
        )
        return

    if interaction.guild:
        if not interaction.guild.me:
            await interaction.followup.send(
                "⚠️ **I'm not installed in this server!**\n\n"
                "You have two options:\n"
                "1️⃣ **Use me in DMs**: Send me a direct message and use this command there\n"
                "2️⃣ **Add me to this server**: Ask a server admin to invite me\n\n"
                "💡 *Tip: All search commands work perfectly in DMs!*",
                ephemeral=True,
            )
            return

        if interaction.channel:
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if permissions.send_messages and permissions.embed_links:
                try:
                    await interaction.followup.send(
                        f"🔍 Found **{len(results)}** hackathon(s) from **{name}**:"
                    )
                    await send_hackathon_notifications(
                        client, results, target_channel=interaction.channel
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "⚠️ **Permission Error**: I don't have permission to send messages in this channel.",
                        ephemeral=True,
                    )
                except Exception as e:
                    logging.error(f"Error sending hackathons to channel: {e}")
                    await interaction.followup.send(
                        "⚠️ An error occurred while sending the results.", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                "⚠️ Unable to determine the channel context.", ephemeral=True
            )
    else:
        logging.info(
            f"Sending {len(results)} platform results to user {interaction.user.id} via DM with pagination"
        )
        try:
            paginator = HackathonPaginator(results, context_type="dm")
            msg, embed, view_buttons = paginator.create_embed()
            paginator.add_action_buttons(view_buttons)
            await interaction.followup.send(
                content=f"🔍 Found **{len(results)}** hackathon(s) from **{name}**:\n\n{msg}",
                embed=embed,
                view=paginator,
            )
            logging.info(f"Sent paginated platform results to user {interaction.user.id}")
        except Exception as e:
            logging.error(f"Failed to send paginated platform results: {e}")
            await interaction.followup.send(
                f"⚠️ Error displaying hackathons. Found {len(results)} results but couldn't display them properly.",
                ephemeral=True,
            )


@client.tree.command(name="upcoming", description="Get hackathons starting in the next X days")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(days="Number of days to look ahead (default 7)")
async def upcoming(interaction: discord.Interaction, days: int = 7):
    await interaction.response.defer(thinking=True)
    db = SessionLocal()
    try:
        results = get_upcoming_hackathons(db, days)
    except Exception as e:
        logging.error(f"Error fetching upcoming hackathons: {e}")
        await interaction.followup.send(
            "❌ An error occurred while fetching upcoming hackathons. Please try again later.",
            ephemeral=True,
        )
        return
    finally:
        db.close()

    if not results:
        await interaction.followup.send(
            f"❌ No upcoming hackathons found in the next **{days}** days.", ephemeral=True
        )
        return

    if interaction.guild:
        if not interaction.guild.me:
            await interaction.followup.send(
                "⚠️ **I'm not installed in this server!**\n\n"
                "You have two options:\n"
                "1️⃣ **Use me in DMs**: Send me a direct message and use this command there\n"
                "2️⃣ **Add me to this server**: Ask a server admin to invite me\n\n"
                "💡 *Tip: All search commands work perfectly in DMs!*",
                ephemeral=True,
            )
            return

        if interaction.channel:
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if permissions.send_messages and permissions.embed_links:
                try:
                    await send_hackathon_notifications(
                        client, results, target_channel=interaction.channel
                    )
                except discord.Forbidden:
                    await interaction.followup.send(
                        "⚠️ **Permission Error**: I don't have permission to send messages in this channel.",
                        ephemeral=True,
                    )
                except Exception as e:
                    logging.error(f"Error sending hackathons to channel: {e}")
                    await interaction.followup.send(
                        "⚠️ An error occurred while sending the results.", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "⚠️ I found hackathons, but I don't have permission to send messages or embeds in this channel.",
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                "⚠️ Unable to determine the channel context.", ephemeral=True
            )
    else:
        logging.info(
            f"Sending {len(results)} upcoming results to user {interaction.user.id} via DM with pagination"
        )
        try:
            paginator = HackathonPaginator(results, context_type="dm")
            msg, embed, view_buttons = paginator.create_embed()
            paginator.add_action_buttons(view_buttons)
            await interaction.followup.send(
                content=f"📅 Found **{len(results)}** upcoming hackathon(s) in the next **{days}** days:\n\n{msg}",
                embed=embed,
                view=paginator,
            )
            logging.info(f"Sent paginated results to user {interaction.user.id}")
        except Exception as e:
            logging.error(f"Failed to send paginated hackathons: {e}")
            await interaction.followup.send(
                f"⚠️ Error displaying hackathons. Found {len(results)} results but couldn't display them properly.",
                ephemeral=True,
            )


@client.tree.command(
    name="subscribe", description="Subscribe to hackathon notifications for a specific theme"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(theme="The theme to subscribe to (e.g., AI, Blockchain)")
async def subscribe(interaction: discord.Interaction, theme: str):
    await interaction.response.defer(ephemeral=True)
    db = SessionLocal()
    try:
        sub, is_new = subscribe_user(db, interaction.user.id, theme)
        if is_new:
            await interaction.followup.send(
                f"✅ You have successfully subscribed to **{theme}** updates!"
            )
        else:
            await interaction.followup.send(f"ℹ️ You are already subscribed to **{theme}**.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error subscribing: {str(e)}")
        logging.error(f"Error in subscribe command: {e}")
    finally:
        db.close()


@client.tree.command(
    name="unsubscribe", description="Unsubscribe from hackathon notifications for a specific theme"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(theme="The theme to unsubscribe from")
async def unsubscribe(interaction: discord.Interaction, theme: str):
    await interaction.response.defer(ephemeral=True)
    db = SessionLocal()
    try:
        removed = unsubscribe_user(db, interaction.user.id, theme)
        if removed:
            await interaction.followup.send(
                f"✅ You have successfully unsubscribed from **{theme}** updates."
            )
        else:
            await interaction.followup.send(f"ℹ️ You were not subscribed to **{theme}**.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error unsubscribing: {str(e)}")
        logging.error(f"Error in unsubscribe command: {e}")
    finally:
        db.close()


@client.tree.command(name="subscriptions", description="View all your theme subscriptions")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def subscriptions(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db = SessionLocal()
    try:
        user_subs = get_user_subscriptions(db, interaction.user.id)
        if not user_subs:
            embed = discord.Embed(
                title="📋 Your Subscriptions",
                description="You don't have any active subscriptions yet.\n\nUse `/subscribe [theme]` to start receiving notifications!",
                color=discord.Color.blue(),
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="📋 Your Subscriptions",
            description=f"You're subscribed to **{len(user_subs)}** theme(s):",
            color=discord.Color.green(),
        )
        themes_list = "\n".join([f"• **{sub.theme}**" for sub in user_subs])
        embed.add_field(name="Active Themes", value=themes_list, inline=False)
        embed.set_footer(text="💡 Use /unsubscribe [theme] to remove a subscription")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching subscriptions: {str(e)}")
        logging.error(f"Error in subscriptions command: {e}")
    finally:
        db.close()


@client.tree.command(name="pause", description="Pause hackathon notifications.")
@app_commands.checks.has_permissions(administrator=True)
async def pause(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db = SessionLocal()
    try:
        success = pause_notifications(db, str(interaction.guild_id))
        if success:
            embed = discord.Embed(
                title="⏸️ Notifications Paused",
                description="Hackathon notifications have been paused for this server.\n\nUse `/resume` to start again.",
                color=discord.Color.orange(),
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Setup Required",
                description="Please run `/setup` first to configure the bot.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error pausing notifications: {str(e)}")
        logging.error(f"Error in pause command: {e}")
    finally:
        db.close()


@pause.error
async def pause_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need Administrator permissions to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", ephemeral=True
        )


@client.tree.command(name="resume", description="Resume hackathon notifications.")
@app_commands.checks.has_permissions(administrator=True)
async def resume(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    db = SessionLocal()
    try:
        success = resume_notifications(db, str(interaction.guild_id))
        if success:
            embed = discord.Embed(
                title="▶️ Notifications Resumed",
                description="Hackathon notifications have been resumed for this server.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Setup Required",
                description="Please run `/setup` first to configure the bot.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error resuming notifications: {str(e)}")
        logging.error(f"Error in resume command: {e}")
    finally:
        db.close()


@resume.error
async def resume_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You need Administrator permissions to use this command.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}", ephemeral=True
        )


@client.tree.command(name="help", description="View all available commands")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 HackRadar Commands",
        description="Here's everything you can do with HackRadar:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="🔧 Server Setup",
        value="- `/setup` - Configure bot preferences\n- `/pause` - Pause notifications\n- `/resume` - Resume notifications\n*Requires Manage Server permission*",
        inline=False,
    )
    embed.add_field(
        name="🔍 Search & Browse",
        value="- `/search [keyword]` - Search hackathons\n- `/upcoming [days]` - Hackathons starting soon\n- `/platform [name]` - Filter by platform",
        inline=False,
    )
    embed.add_field(
        name="🔔 Personal Alerts",
        value="- `/subscribe [theme]` - Get DM alerts\n- `/unsubscribe [theme]` - Stop DM alerts\n- `/subscriptions` - View your subscriptions",
        inline=False,
    )
    embed.add_field(
        name="ℹ️ Info & Support",
        value="- `/about` - About HackRadar\n- `/help` - Show this message",
        inline=False,
    )
    embed.set_footer(text="💡 Tip: Run /setup first to start receiving notifications")
    embed.set_thumbnail(url=client.user.display_avatar.url)

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="Star on GitHub",
            style=discord.ButtonStyle.link,
            url="https://github.com/Spartan-71/Discord-Hackathon-Bot",
            emoji="⭐",
        )
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@client.tree.command(name="about", description="Learn about HackRadar")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚀 About HackRadar",
        description=(
            "HackRadar is an open-source Discord bot that aggregates hackathons "
            "from multiple platforms and delivers personalized notifications.\n\n"
            f"**Version:** 1.0.0\n"
            f"**Servers:** {len(client.guilds):,}\n"
            f"**Platforms:** Devfolio, Devpost, Unstop, DoraHacks, MLH, Hack2Skill and Kaggle\n"
        ),
        color=discord.Color.blue(),
    )
    if client.user:
        embed.set_thumbnail(url=client.user.display_avatar.url)
    embed.set_footer(text="Made with 💙 by Spartan-71")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="⭐ Star on GitHub",
            style=discord.ButtonStyle.link,
            url="https://github.com/Spartan-71/Discord-Hackathon-Bot",
        )
    )
    view.add_item(
        discord.ui.Button(
            label="🐛 Report Bug",
            style=discord.ButtonStyle.link,
            url="https://github.com/Spartan-71/Discord-Hackathon-Bot/issues",
        )
    )
    view.add_item(
        discord.ui.Button(
            label="💬 Support Server",
            style=discord.ButtonStyle.link,
            url="https://discord.gg/3pM6yJBE",
        )
    )
    await interaction.response.send_message(embed=embed, view=view)


# 7. Background Tasks


@tasks.loop(hours=12)
async def check_and_notify_hackathons(bot: MyClient):
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
        await send_hackathon_notifications(bot, new_hackathons)
        await notify_subscribers(bot, new_hackathons)
        logging.info("Completed hackathon notifications")
    except Exception as e:
        logging.error(f"Error in check_and_notify_hackathons task: {e}")


@check_and_notify_hackathons.before_loop
async def before_check_and_notify():
    await client.wait_until_ready()


# 8. Main Execution

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in the environment")
    client.run(token)
