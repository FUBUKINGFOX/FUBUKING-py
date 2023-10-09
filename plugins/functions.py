import discord
from discord.ext import commands
from bin.class_init.plugin_init import plugin_init
import time
from bin import config_loader
class functions(plugin_init):
     #===========================

    @commands.command()
    async def channel_server(self, ctx: commands.Context,rtc_server: str=None ,  channel :discord.VoiceChannel=None) :
        if channel == None :
            try :
                channel = ctx.author.voice.channel
            except Exception :
                embed = discord.Embed(title="", description="No channel to connect. Please call `/connect` from a voice channel.", color=0xff0000)
                await ctx.send(embed=embed)
                return
            
        if  channel.rtc_region == None :
            rtc = "auto"
        else :
            rtc = channel.rtc_region

        if rtc_server == None :
            embed = (discord.Embed(title="Voice Channel INFO",color=0xff00f2)
                    .add_field(name="target channel:",value=f"{channel.mention}")
                    .add_field(name="rtc_server:",value=f"```{rtc}```"))
            await ctx.send(embed=embed)
            return
        
        elif rtc_server == "auto" :
            rtc_server = None

        elif rtc_server == "list" :
            embed = discord.Embed(color=0x8aff8a,
                                  title="RTC Server list",
                                  description="`auto`自動\n`brazil`巴西\n`hongkong`香港\n`india`印度\n`japan`日本\n`rotterdam`鹿特丹\n`russia`俄羅斯\n`singapore`新加坡\n`southafrica`南非\n`sydney`悉尼\n`us-central`中美\n`us-east`東美\n`us-south`南美\n`us-west`西美")
            await ctx.send(embed=embed)
            return
        
        try :
            await channel.edit(rtc_region=rtc_server)
        except discord.HTTPException :
            await ctx.send("error code: [404]")
            return
        
        embed = (discord.Embed(title = "Change RTC Server",color = 0xff00f2)
                .add_field(name="target channel:",value=f"{channel.mention}")
                .add_field(name="rtc_server:", value=f"```{rtc}==>{rtc_server}```"))
        await ctx.send(embed=embed)


    #===========================


    @commands.command(aliases=["fuck"])
    async def msg_handler(self, ctx) :
        time.sleep(1)
        await ctx.message.delete()
        await ctx.send('<:OKO:1028581472749240362>')
        try :
            await ctx.author.move_to(channel=None)
        except Exception :
            pass
    
     #=========================== 
        


async def setup(bot) :
    await bot.add_cog(functions(bot))