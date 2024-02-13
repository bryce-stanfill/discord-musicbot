import discord
from discord.ext import commands
from discord import app_commands
import youtube_dl as ytdl
import asyncio
import random
from paginator import CustomPaginator
from app import guild_ids

# for all the guilds that the bot is in and can be initialized on

ytdl.utils.bug_reports_message = lambda: ""

ytdlOptions = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpegOptions = {
    'options': '-vn',
}

# only interested in streaming music, not downloading or using music from local computer

class MusicStuff(commands.Cog):

    def __init__(self, bot : commands.Bot):
        self.bot = bot
        self.description = "Music commands"
        # list holding the song queues, let's say the limit is 50
        self.queueList = []
        self.limit = 50
        self.vc : discord.VoiceClient = None
        # when connected to the voice channel, default state is the player playing
        self.isPaused = False
        # whether or not to loop the current song being played
        self.loop = False

        self.currentSong = None
        self.ytdl = ytdl.YoutubeDL(ytdlOptions)
        # paginator for the queue command, default is 5 commands per page
        self.paginator = CustomPaginator(self.queueList)

    # ------------- COMMANDS -------------

    '''
    The play command works like a queuing and play command. The current song being played is not in queue list as the queue list represents the songs
    that are waiting to be played. The queue allows duplicates of songs.
    
    '''
    @commands.hybrid_command(name = "play", description = "plays a video from youtube, behaves like a queuing command as well")
    @app_commands.guilds(*guild_ids)
    async def play(self, ctx : commands.Context, url : str):
        if ctx.author.voice:
            data = None
            channel = ctx.author.voice.channel
            if self.vc:
                if self.vc.channel.id != channel.id:
                    await self.vc.move_to(channel)
            else:
                await channel.connect()
            
            self.vc = ctx.voice_client
            loop = asyncio.get_event_loop()
            
            await ctx.defer()

            async with ctx.typing():
                # throws youtube_dl (ytdl here).DownloadError if it is not a youtube link
                try:
                    data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(url, download=False))
                
                except ytdl.DownloadError as e:
                    embed = discord.Embed(color=0xec0000, description="Unsupported url! Do a youtube video or playlist link!")
                    await ctx.send(embed=embed)
                    return
                
            # check if the url parameter was a search, return if "url" is a search
            if data["extractor_key"] and data["extractor_key"] == "YoutubeSearch":
                    embed = discord.Embed(color=0xec0000, description="Search query detected! Enter a youtube video or playlist link")
                    await ctx.send(embed=embed, ephemeral=True)
                    return

             # send default discord youtube embed
            await ctx.channel.send(url)

            # process both youtube playlist links and normal youtube video links
            if "entries" in data or data:
                # playlist link
                # print(data["entries"][i]["url"]), data["entries"][i] also includes each individual video's title in the playlist
                # to get playlist title: data["title"]
                # video link
                # print(data["url"])
                i = 0
                
                if len(self.queueList) > 0 and len(self.queueList) < self.limit:
                    # playlist link
                    if "entries" in data:
                        while len(self.queueList) < self.limit and i < len(data["entries"]):
                            data["entries"][i]["short-url"] = url
                            self.queueList.append(data["entries"][i])
                            i = i + 1
                        
                        # not all songs in the playlist could be put into the queue due to storage being full
                        if i < len(data["entries"]):
                            embed = discord.Embed(color=0xec0000, description="Could not put all songs in the youtube playlist")
                            await ctx.send(embed=embed, ephemeral=True)
                        
                    # video link(separated due to different keys in the data dictionary)
                    else:
                        data["short-url"] = url
                        self.queueList.append(data)

                elif len(self.queueList) == 0:
                    if "entries" in data:
                        data["entries"][0]["short-url"] = url
                        if self.currentSong:
                            self.queueList.append(data["entries"][0])

                        i = i + 1
                        while len(self.queueList) < self.limit and i < len(data["entries"]):
                            data["entries"][i]["short-url"] = url
                            self.queueList.append(data["entries"][i])
                            i = i + 1

                        if i < len(data["entries"]):
                            embed = discord.Embed(color=0xec0000, description="Could not put all songs in the youtube playlist")
                            await ctx.send(embed=embed, ephemeral=True)
                        
                        if not self.currentSong:
                            data = data["entries"][0]
                    else:
                        data["short-url"] = url
                        if self.currentSong:
                            self.queueList.append(data)
                        
                else:
                    await ctx.send("Error fulfilling {} request".format(ctx.message.content[5:]))

            if not self.currentSong: 
                player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(data["url"], **ffmpegOptions), volume=0.5)
                self.vc.play(player, after=lambda e: print("{} thrown! Error playing audio!".format(e.__class__)) if e else self.bot.dispatch("nextSong", ctx))
                self.currentSong = data
                self.isPaused = False
                title = data["title"] + " by " + data["channel"]
                embed = discord.Embed(color=0xd94ff, title=title, description="Now Playing!")
                await ctx.send(embed=embed)
            else:
                embed = None
                if "entries" not in data:
                    embed = discord.Embed(color=0xd94ff, title= "{} by {} added to the queue!".format(data["title"], data["channel"]), description="Added to the queue!")
                else:
                    playlistTitle = data["title"]
                    embed = discord.Embed(color=0xd94ff, description="Added songs from {} playlist into the queue".format(playlistTitle))

                await ctx.send(embed=embed)

            # keep queuelists consistent between this class and paginator
            await self.paginator.defaultBack(self.queueList)
            
                
        else:
            embed = discord.Embed(color=0xec0000, description="You're not connected to a voice channel!")
            await ctx.send(embed=embed, ephemeral=True)
        

    # end command for when a user forcefully ends song
    @commands.hybrid_command(name = "next", description = "skips to next song on the queue list(stops current song even if there are no songs in the queue)")
    @app_commands.guilds(*guild_ids)
    async def next(self, ctx : commands.Context):
        # check if bot is still connected to a voice channel(bot can disconnect through discord gui and can be used to skip to next song or other operations)
        if ctx.author.voice.channel and self.vc:
            self.vc.stop()
            # on_nextsong(self, ctx) dequeues the next song in the queue and takes care of the rest
            if len(self.queueList) > 0:
                self.loop = False
                embed = discord.Embed(color=0xd94ff, description="Next song in the queue now being played!")
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=0xec0000, description="No new song in the queue!")
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0xec0000)
            if not ctx.author.voice.channel:
                embed.description = "You're not connected to a voice channel!"
            else:
                embed.description = f"{self.bot.user.name} is not in a voice channel!"
    
            await ctx.send(embed=embed)


    @commands.hybrid_command(name = "pause", description = "pauses current song being played")
    @app_commands.guilds(*guild_ids)
    async def pause(self, ctx : commands.Context):
        if ctx.author.voice.channel and self.vc:
            if not self.isPaused and self.currentSong:
                # two separate embeds since color can only be declared at initialization
                embed = discord.Embed(color=0xd94ff)
                embed.add_field(name="{}".format(self.currentSong["title"]),value="Now paused!")
        
                self.vc.pause()
                self.isPaused = True
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(color=0xec0000)
                if not self.currentSong:
                    embed.description = "There is no current song playing!"
            
                else:
                    embed.add_field(name="{}".format(self.currentSong["title"]), value="is already paused!")
                
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0xec0000)
            if not ctx.author.voice.channel:
                embed.description = "You're not connected to a voice channel!"
            else:
                embed.description = f"{self.bot.user.name} is not in a voice channel!"
    
            await ctx.send(embed=embed)

    # get the titles of the songs from the queue list
    @commands.hybrid_command(name = "queue", description = "view the current song queue")
    @app_commands.guilds(*guild_ids)
    async def queue(self, ctx : commands.Context):
        if len(self.queueList) == 0:
            embed = discord.Embed(color=0xd94ff, description="Current queue is empty!")
            await ctx.send(embed=embed)
        else:
            await self.paginator.sendQueueMenu(ctx)

    @commands.hybrid_command(name = "resume", description = "resumes current song being played")
    @app_commands.guilds(*guild_ids)
    async def resume(self, ctx : commands.Context):
        if ctx.author.voice.channel and self.vc:
            if self.isPaused and self.currentSong:
                embed = discord.Embed(color=0xd94ff)
                embed.add_field(name="{}".format(self.currentSong["title"]), value="Now resuming!")
                await ctx.send(embed=embed)
                self.vc.resume()
                self.isPaused = False
            else:
                embed = discord.Embed(color=0xec0000)
                if not self.currentSong:
                    embed.description = "There is no current song playing!"
            
                else:
                    embed.add_field(name="{}".format(self.currentSong["title"]), value="is already playing!")
                
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0xec0000)
            if not ctx.author.voice.channel:
                embed.description = "You're not connected to a voice channel!"
            else:
                embed.description = f"{self.bot.user.name} is not in a voice channel!"
    
            await ctx.send(embed=embed)


    @commands.hybrid_command(name = "empty", description = "empties the current song queue")
    @app_commands.guilds(*guild_ids)
    async def empty(self, ctx : commands.Context):
        await self.emptyQueue()
        embed = discord.Embed(color=0xd94ff, description="Queue is now empty!")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name = "leave", description = "leaves current voice channel")
    @app_commands.guilds(*guild_ids)
    async def leave(self, ctx : commands.Context):
        if self.vc:
            await ctx.guild.voice_client.disconnect()
            # let disconnect event handler handle extra code
            embed = discord.Embed(color=0xd94ff, description="disconnected from voice channel")
            await self.bot.invoke(self.empty(ctx))
            await self.paginator.defaultBack(self.queueList)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0xec0000, description="Not in a voice channel to leave!")
            await ctx.send(embed=embed)

    @commands.hybrid_command(name = "shuffle", description = "shuffles the current song queue in a random order")
    @app_commands.guilds(*guild_ids)
    async def shuffle(self, ctx : commands.Context):
        if len(self.queueList) > 0:
            random.shuffle(self.queueList)
            await self.paginator.defaultBack(self.queueList)
            embed = discord.Embed(color=0xd94ff, description="Queue list has been shuffled!")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=0xec0000, description="Can't shuffle the queue list since it's empty!")
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name = "current", description = "Gives information about what current song is playing")
    @app_commands.guilds(*guild_ids)
    async def current(self, ctx: commands.Context):
        if self.currentSong:
            embed = discord.Embed(color=0xd94ff)
            embed.add_field(name="{} by {}".format(self.currentSong["title"], self.currentSong["channel"]), value="currently being played!")
        else:
            embed = discord.Embed(color=0xec0000, description="No current song being played!")
            
        await ctx.send(embed=embed)

    @commands.hybrid_command(name = "looping", description = "Enables or disables looping on current song (default set to false)")
    @app_commands.guilds(*guild_ids)
    async def looping(self, ctx : commands.Context):
        if self.loop:
            self.loop = False
        else:
            self.loop = True
        
        embed = discord.Embed(color=0xd94ff, description="current song looping set to {}".format(self.loop))
        await ctx.send(embed=embed)

    # empty function helper
    async def emptyQueue(self):
        if len(self.queueList) > 0:
            for i in range(len(self.queueList)):
                self.queueList.pop(0)
            await self.paginator.defaultBack(self.queueList)

    # --------------- EVENTS OR LISTENERS -----------------


    # checks if bot left voice channel from gui in discord or disconnected from the leave command
    @commands.Cog.listener()
    async def on_voice_state_update(self, member : discord.Member, before : discord.VoiceState, after : discord.VoiceState):
        # check the specific instance where the member is a bot(this bot), connected to a voice channel, and then not connected to a voice channel
        if before and member.bot and member.id == self.bot.user.id:
            self.isPaused = False
            self.vc = None
            self.currentSong = None
            await self.emptyQueue()

     # next command listener for when the song ends
    @commands.Cog.listener()
    async def on_nextSong(self, ctx : commands.Context):
        if len(self.queueList) > 0 or self.loop:

            # if looping is enabled, keep looping the current song, otherwise get the next song from the queue
            if not self.loop:
                data = self.queueList.pop(0)
                await self.paginator.defaultBack(self.queueList)
            else:
                data = self.currentSong
            player = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(data["url"], **ffmpegOptions), volume=0.6)

            try:
                self.vc.play(player, after=lambda e: print("{} thrown! Error playing audio!".format(e.__class__)) if e else self.bot.dispatch("nextSong", ctx))
            # queued the songs when a current song is playing(this includes when it is paused)
            except discord.ClientException as e:
                pass
            else:
                self.isPaused = False
                self.currentSong = data
                embed = discord.Embed(color=0xd94ff, title=data["title"] + " by " + data["channel"], description="Now Playing!")
                await ctx.send(embed=embed)


                # send default discord youtube embed, sends playlist link embed if the entry is from a playlist link
                await ctx.channel.send(data["short-url"])
 

        else:
            embed = discord.Embed(color=0xd94ff, description="There are no more songs to be played. Use the /play command to add more songs or play current song choice. \
                                                              Also can have the bot leave the current voice channel with /leave.")
            await ctx.send(embed=embed)
            self.currentSong = None


async def setup(bot : commands.Bot):
    await bot.add_cog(MusicStuff(bot), guilds = [discord.Object(id=value) for value in guild_ids])