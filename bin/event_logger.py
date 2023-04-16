from discord.ext import commands
from bin import ctc, ctt
def cmd_error_logger(context: commands.Context,msg) :
    ctc.printRed(f"{ctt.time_now()}:[CMD]: ERROR     : {context.guild.name}/{context.channel} :: {msg} \n")
def cmd_info_logger(context: commands.Context,msg) :
    ctc.printBlue(f"{ctt.time_now()}:[CMD]: INFO      : {context.guild.name}/{context.channel} :: {msg} \n")
def cmd_warn_logger(context: commands.Context,msg) :
    ctc.printYellow(f"{ctt.time_now()}:[CMD]: WARN      : {context.guild.name}/{context.channel} :: {msg} \n")
def error_logger(msg) :
    ctc.printDarkYellow(f"{ctt.time_now()}:[SYSTEM]: ERROR     :: {msg}\n")
def info_logger(msg) :
    ctc.printBlue(f"{ctt.time_now()}:[SYSTEM]: INFO      :: {msg}\n")
def warn_logger(msg) :
    ctc.printYellow(f"{ctt.time_now()}:[SYSTEM]: WARN      :: {msg}\n")
