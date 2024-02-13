import discord
from discord.ext import commands
from discord.ui import Button, View
import math

class CustomPaginator:

    def __init__(self, queueList : list, entriesPerPage : int = 5):
        self.queueList = queueList
        self.numPages = math.ceil(float(len(self.queueList)) / entriesPerPage)
        self.currentPage = 1
        self.entriesPerPage = entriesPerPage
        self.buttons = [Button(label="<< Prev", style=discord.ButtonStyle.blurple, custom_id="prev"), 
        Button(label=f"{self.currentPage} / {self.numPages}", style=discord.ButtonStyle.gray, disabled=True, custom_id="page num"), 
        Button(label="Next >>", style=discord.ButtonStyle.blurple, custom_id="next")]

        # this is the embed to add to and switch from
        self.embed = discord.Embed(title="Queue List", type="rich", color=0x3498db)
        # the message that will be sent that will contain the queue (deletes embed whenever the queue changes)
        # deletes the message attribute(whole embeded message) when the queue changes (item added or removed), CustomPaginator object will be updated with
        # new attribute values and defaulted back to original values (self.length, self.numPages, self.message, and self.currentPage will be updated) from the 
        # defaultBack function
        self.message : discord.Message = None

    # creates each individual page (without including the buttons, View does that)
    def updateQueueMenu(self):
        self.buttons[1].label = f"{self.currentPage} / {self.numPages}"
        self.embed.clear_fields()
        
        '''
        The way this section works, is that n represents the current page that is being represented. Each page has a numbered list 
        of songs, where 5(n - 1) + 1 = 5n - 4 to 5n, is the numbering range for the songs in the queue. Or more precisely and generically, let p = entriesPerPage, 
        n = currentPage, song numbering : [pn - p, pn], where n in [1, self.numPages]

        an song entry on the nth page in the jth iteration = (self.currentPage - 1) * self.entriesPerPage + j
        
        '''
        for j in range(1, self.entriesPerPage + 1):
            index = (self.currentPage - 1) * self.entriesPerPage + j - 1
            if index < len(self.queueList):
                title = self.queueList[index]["title"]
                self.embed = self.embed.add_field(name=f"{index + 1}. ", value=f"{title}", inline=False)
            else:
                break 
            

    async def sendQueueMenu(self, ctx : commands.Context):
        view = View(timeout = None)
        for i in self.buttons:
            view.add_item(i)
        self.updateQueueMenu()
        self.message = await ctx.send(embed=self.embed, view=view)

        # go to the previous page(circular)
        async def prevButtonCallback(interaction : discord.Interaction):
            self.currentPage = ((self.currentPage - 2) % self.numPages) + 1
            
            await interaction.response.defer()
            self.updateQueueMenu()
            await self.message.edit(embed=self.embed, view=view)

        # go to the next page(circular)
        async def nextButtonCallback(interaction : discord.Interaction):
            self.currentPage = self.currentPage % self.numPages + 1
            
            await interaction.response.defer()
            self.updateQueueMenu()
            await self.message.edit(embed=self.embed, view=view)


        self.buttons[0].callback = prevButtonCallback
        self.buttons[2].callback = nextButtonCallback    


    async def defaultBack(self, queueList : list):
        # change the queue contents in this class 
        self.queueList = queueList
        self.numPages = math.ceil(float(len(self.queueList)) / self.entriesPerPage)
        self.currentPage = 1
        # delete the current queue message when the queue changes
        if self.message:
            await self.message.delete()
            self.message = None


