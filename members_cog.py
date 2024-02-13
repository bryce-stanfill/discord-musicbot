import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from app import guild_ids

class Members(commands.Cog):

    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.description = "Does member utilities and other stuff"

    # ------ events ------

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        channel = discord.utils.get(member.guild.channels, name="general")
        await channel.send(f"Welcome {member.name} to {member.guild}")

    @commands.Cog.listener()
    async def on_member_remove(self, member : discord.Member):
        channel = discord.utils.get(member.guild.channels, name="general")
        await channel.send(f"Farewell {member.name}!")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.", ephemeral = True)
        else:
            await ctx.send("command failed", ephemeral = True)


    # ----- commands -----

    # name is explicitly needed inside for the slash command
    @commands.hybrid_command(name = "ban", description = "bans someone")
    @commands.has_permissions(ban_members=True)
    @app_commands.guilds(*guild_ids)
    # have the member argument as a User instead of a Member for discord autocompletion of member names
    async def ban(self, ctx : commands.Context, member : discord.User, reason=None):
        server = ctx.channel.guild.name
        if member and not member.bot and member.name != ctx.author.name:
            await member.send(f"You've been banned from {server} due to {reason}")
            await member.ban(reason = reason)
            await ctx.send(f"{member.name} banned from the server due to {reason}")
        else:
            await ctx.send(f"{member} not found or applicable!", ephemeral=True)

    @commands.hybrid_command(name = "tempban", description = "bans someone temporarily(time in seconds, default 5 seconds)")
    @commands.has_permissions(ban_members=True)
    @app_commands.guilds(*guild_ids)
    async def tempban(self, ctx : commands.Context, member : discord.User, time= 5, reason=None):
        if member and not member.bot and member.name != ctx.author.name:
            await ctx.send(f"{member.name} is banned for {time} seconds!")
            await member.send(f"You've been banned from {ctx.channel.guild.name} due to {reason} for {time} seconds")
            await member.ban(reason = reason)
            await asyncio.sleep(time)
            # in case the unban command was called during the limited time ban
            try:
                await ctx.guild.unban(member, reason=f"tempban {time} seconds")
            except discord.NotFound as e:
                return
            await ctx.channel.send(f"{member.name} is now unbanned from the server")
        else:
            await ctx.send(f"{member} not found or applicable!", ephemeral=True)
        
    @commands.hybrid_command(name = "unban", description = "unbans someone")
    @commands.has_permissions(administrator=True)
    @app_commands.guilds(*guild_ids)
    async def unban(self, ctx: commands.Context, user : discord.User, reason=None):
        try:
            await ctx.guild.fetch_ban(user)
        except discord.NotFound as e:
            await ctx.reply(f"{user.name} is not currently banned from the server", ephemeral=True)
        else:
            await ctx.guild.unban(user, reason=None)
            await user.send(f"You've been unbanned from {ctx.channel.guild.name} due to {reason}")
            await ctx.reply(f"{user.name} is now unbanned from the server")


async def setup(bot):
    await bot.add_cog(Members(bot), guilds = [discord.Object(id=value) for value in guild_ids])
