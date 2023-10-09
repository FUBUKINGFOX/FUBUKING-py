import configparser
import asyncio
import os
import sys
import getopt
import discord 
from discord.ext import commands
#===============
from bin import ctc, ctt, token, event_logger, source
from bin.class_init.plugin_init import plugin_init

config = configparser.ConfigParser()
config.read("./config/config.ini")
listener_port = config["MAIN"].getint("listener_port")
prefix = ["!"]
intents = discord.Intents.all()
bot = commands.Bot(intents=intents,command_prefix=prefix)
#===============app start
argv = sys.argv[1:]
arg_token = None
try:
    opts, args = getopt.getopt(argv,"ht:",["token="])
except getopt.GetoptError:
    print ('main.py -t <token>')
    sys.exit(2)
for opt, arg in opts:
      if opt == '-h':
         print ('main.py -t <token>')
         sys.exit(0)
      elif opt in ("-t", "--token"):
         arg_token = arg
#=================
@bot.command(name="shutdown")
async def shutdown(ctx :commands.Context):
    await bot.change_presence(status=discord.Status.invisible)
    await ctx.send(f"> {source.off_cv()}")
    await bot.close()




#==========================================================
class commands_error_handler(plugin_init) :
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        embed = discord.Embed(title="Command ERROR :", description=f"{error}", color=0xf6ff00)
        await ctx.reply(embed=embed)
        event_logger.cmd_error_logger(ctx, error)
async def load_error_handler():
    await bot.add_cog(commands_error_handler(bot))

async def load_extensions() :
    for cog_files in os.listdir("./plugins") :
        if cog_files.endswith(".py") :
            await bot.load_extension(f"plugins.{cog_files[:-3]}")
        elif cog_files.endswith(".pyc") :
            await bot.load_extension(f"plugins.{cog_files[:-4]}")

bot.command(name="sync_cmd")
async def sync_slash_cmd():
    try :
        slash_cmd = await bot.tree.sync()
        event_logger.info_logger(f"upload {len(slash_cmd)} slash command(s)\n")
    except Exception as error :
        event_logger.error_logger("failed to upload slash command(s)")
        print(f"Exception:\n{error}\n")

@bot.command(name="load",description="Load plugin.")
@commands.is_owner()
async def load(ctx, extension):
    await ctx.message.add_reaction('✅')
    await bot.load_extension(f'plugins.{extension}')
    await ctx.send(f"succeed load `{extension}` plugin")

@bot.command(name="unload",description="Unload plugin.")
@commands.is_owner()
async def unload(ctx, extension):
    if extension == "commands_error_handler" :
        await ctx.send("Can't unload this plugin.")
    else:
        await ctx.message.add_reaction('⚠️')
        await bot.unload_extension(f'plugins.{extension}')
        await ctx.send(f"succeed unload `{extension}` plugin")

@bot.command(name="reload",description="Reload plugin.")
@commands.is_owner()
async def reload(ctx, extension):
    await ctx.message.add_reaction('🔄')
    await bot.reload_extension(f'plugins.{extension}')
    await ctx.send(f"succeed reload `{extension}` plugin")
#==========================================================
@bot.event
async def on_ready() :
    os.system("cls")
    ctc.printSkyBlue("Discord Bot Server [版本 a.0.0.1]\n")
    ctc.printDarkBlue("[MIT License]Copyright (c) 2023 FUBUKINGFOX. 著作權所有，並保留一切權利。\n")
    ctc.printGreen(u'Logged in as:\n'.format(bot))
    ctc.printPink(u'{0.user.name}\n'.format(bot))
    ctc.printYellowBlue(u'{0.user.id}\n'.format(bot))
    game = discord.Activity(type=discord.ActivityType.listening, name='YouTube')
    await bot.change_presence(activity=game, status=discord.Status.idle)
       
    try :
        id = bot.get_channel(listener_port)
        await id.send(u'💽:{0.user.name}`{0.user.id}`'.format(bot)) 
    except :
        pass

async def start(token):
    async with bot:
        await load_extensions()
        await load_error_handler()
        await bot.start(token=token, reconnect=True)

if __name__ == "__main__" :
    ctc.printDarkGray(f"{ctt.time_now()}connecting to discord...\n")
    asyncio.run(start(token.token(arg_token)))
