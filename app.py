import discord
from discord.ext import commands
from discord import app_commands

guild_ids = []
        
class Chat(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.description = "These are chat commands"
    
    @commands.hybrid_command(name = "test", description="This is a test command... doesn't really do anything")
    @app_commands.guilds(*guild_ids)
    async def test(self, ctx : commands.Context):
        await ctx.send("testing...")
        
    # called when using non-slash commands(prefix = !)
    @commands.Cog.listener()
    async def on_command_error(self, ctx : commands.Context, error):
        #error = getattr(error, "exception", error)
        if(isinstance(error, commands.CommandNotFound)):
            await ctx.send(f"{ctx.message.content[1:]} not a valid command!")
        

async def setup(bot):
    global guild_ids
    # have a predetermined list of guild/server ids for personal use
    try:
        with open("guild_ids.txt", "r") as f:
            for line in f:
                guild_ids.append(int(line.strip()))
    except FileNotFoundError:
        print("failed to load file, terminating now")

    if len(guild_ids) > 0:
        await bot.add_cog(Chat(bot), guilds = [discord.Object(id=val) for val in guild_ids])
