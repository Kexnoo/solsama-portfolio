import discord
from discord.ext import commands
from discord import app_commands
import json
import os

AFFINITY_FILE = "sol_affinity.json"


def load_affinities():
    """Load user affinities from file, or create a blank dict."""
    if os.path.exists(AFFINITY_FILE):
        try:
            with open(AFFINITY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Sol affinity file was corrupted — resetting.")
            return {}
    return {}


def save_affinities(data):
    """Save user affinities to file."""
    with open(AFFINITY_FILE, "w") as f:
        json.dump(data, f, indent=4)


class SolDebug(commands.Cog):
    """Cog for debugging and tracking Sol's emotional state and affinities."""

    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "sol_data"):
            bot.sol_data = {
                "mode": "Neutral",
                "energy": 100,
                "affinities": load_affinities()
            }

    def increase_affinity(self, user_id: int, amount: int = 1):
        """Increase Sol's affinity toward a user."""
        affinities = self.bot.sol_data["affinities"]
        affinities[str(user_id)] = affinities.get(str(user_id), 0) + amount
        save_affinities(affinities)

    def get_top_affinities(self, top_n: int = 3):
        """Return the top N user affinities."""
        affinities = self.bot.sol_data["affinities"]
        sorted_affinities = sorted(affinities.items(), key=lambda x: x[1], reverse=True)
        return sorted_affinities[:top_n]

    @app_commands.command(name="sol", description="Check Sol's current mode, energy, and top affinities.")
    async def sol_status(self, interaction: discord.Interaction):
        sol_data = self.bot.sol_data
        top_affinities = self.get_top_affinities()
        embed = discord.Embed(title="Sol Status", color=0xD5A6E5)
        embed.add_field(name="Mode", value=sol_data["mode"], inline=True)
        embed.add_field(name="Energy", value=f"{sol_data['energy']}%", inline=True)
        if top_affinities:
            text = "\n".join(
                [f"<@{uid}> — {score}" for uid, score in top_affinities]
            )
        else:
            text = "No affinity data yet."
        embed.add_field(name="Top Affinities", value=text, inline=False)
        await interaction.response.send_message(embed=embed)

    async def on_message(self, message):
        """Example hook: automatically increase affinity when Sol interacts naturally."""
        if message.author.bot:
            return
        pass


async def setup(bot):
    await bot.add_cog(SolDebug(bot))
