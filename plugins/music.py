#== encoding utf-8 ==
import discord
from discord.ext import commands
import asyncio
import itertools
import sys
import time
import traceback
from async_timeout import timeout
from functools import partial
import youtube_dl
from youtube_dl import YoutubeDL
#===============
from bin import ctc, source,config_loader
from plugins.music_bin import yt_url_exploer, queue_exploer
from FUBUKING import config
enable_special_playchannel = config["music"].getboolean("enable_special_playchannel")
enable_request_banned_song = config["music"].getboolean("enable_request_banned_song")
enable_priorityqueue = config["music"].getboolean("enable_priorityqueue")
enable_yt_cookie =  config["music"].getboolean("enable_yt_cookie")
playchannel = config_loader.load_playchannel()
songs_filter = config_loader.load_songs_filter(config["music"].getboolean("enable_songs_filter"))
banned_song = {}
list_song = {}
loop_list = []
filter_skip = []
list_skip = []
owner_id = [794890107563671553]
#===============
# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdlopts = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'webm',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'verbose': False,
    'source_address': '0.0.0.0',  # ipv6 addresses cause issues sometimes
}
if enable_yt_cookie == True :
    ytdlopts["cookiefile"] = f".\\config\yt-cookie\ytcookie.txt"
    ctc.printDarkYellow(f"cookie_file:  .\\config\yt-cookie\ytcookie.txt\n")

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)
class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""


class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False, creat_Queued_message: bool):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        flag=0#filter
        for j in songs_filter :
            if j in data["title"] :
                flag=1
                break


        if flag == 1 :#filt the song 
            if enable_request_banned_song == True :
                embed = discord.Embed(title="此歌曲可能不適合部分聽眾", description=f"任何人均有跳過這首歌的權限", color=0xf6ff00)
                await ctx.message.reply(embed=embed)
                try :
                    banned_song[ctx.guild.id].append(data['webpage_url'])
                except KeyError :
                    e = [data['webpage_url']]
                    banned_song[ctx.guild.id] = e

                if creat_Queued_message == True :
                    embed = discord.Embed(title="", description=f"Queued [{data['title']}]({data['webpage_url']}) [{ctx.author.mention}]", color=0xf6ff00)
                    await ctx.send(embed=embed)
                if download:
                    source = ytdl.prepare_filename(data)
                else:
                    return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}
                return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)#@@@@@@@@@@@@@@@@@@@@@@@@@@@

            else :
                embed = discord.Embed(title="YABE", description="", color=0xf6ff00)
                await ctx.send(embed=embed)
                return False

        else :
            if creat_Queued_message == True :
                embed = discord.Embed(title="", description=f"Queued [{data['title']}]({data['webpage_url']}) [{ctx.author.mention}]", color=0x73bbff)
                await ctx.send(embed=embed)

            if download:
                source = ytdl.prepare_filename(data)
            else:
                return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

            return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)


    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog
        if enable_priorityqueue :
            self.queue = asyncio.PriorityQueue()
        else :
            self.queue =asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source_ = (await self.queue.get()).item
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source_, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source_, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue


        

            seconds = int(source.duration) % (24 * 3600) 
            hour = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            if hour > 0:
                duration = "%dhours, %dminutes, %dseconds" % (hour, minutes, seconds)
            else:
                duration = "%dminutes, %dseconds" % (minutes, seconds)


            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set) )

            e_color = 0x73d7ff ############__init
            if self._guild.id in filter_skip :
                filter_skip.remove(self._guild.id)
            if self._guild.id in list_skip :
                list_skip.remove(self._guild.id)
            song_type = None

            try :
                if source.web_url in list_song[self._guild.id] :
                    list_song[self._guild.id].remove(source.web_url)
                    list_skip.append(self._guild.id)
                    e_color = 0xffff00
                    song_type = 'list_song' 
            except KeyError:
                pass
            try :
                if source.web_url in banned_song[self._guild.id] :
                    banned_song[self._guild.id].remove(source.web_url)
                    filter_skip.append(self._guild.id)
                    e_color = 0xff5900
                    song_type = 'banned_song'
            except KeyError:
                pass

            embed = (discord.Embed(title='Now playing',
                               description=f'```css\n{source.title}\n```',
                               color=e_color)
                 .add_field(name='Duration', value=duration)
                 .add_field(name='Requested by', value=source.requester.mention)
                 .add_field(name='Uploader', value=f'[{source.uploader}]({source.uploader_url})')
                 .add_field(name='URL', value=f'[Click]({source.web_url})') 
                 .set_thumbnail(url=source.thumbnail))

            if song_type != None :
                embed.add_field(name='song_tag', value=f'#{song_type}') 

            if self._guild.id in loop_list :
                await self.queue.put(queue_exploer.Prioritize(3, source_))
                embed.add_field(name='loop mod', value=f'ON')

            self.np = await self._channel.send(embed=embed)
            
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.totalvotes = []

    async def cleanup(self, guild):
        try:
            guild.voice_client.stop()
            time.sleep(0.5)
            guild.voice_client.play(discord.FFmpegPCMAudio(source=source.seeya), after=None)
            time.sleep(3)
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del list_song[guild.id]
        except KeyError:
            pass

        try:
            del banned_song[guild.id]
        except KeyError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

        if guild.id in loop_list :
            loop_list.remove(guild.id)

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player

        return player

    @commands.command(name='connect', aliases=['join','c'], description="connects to voice channel")
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connect to voice.
        Parameters
        ------------
        channel: discord.VoiceChannel [Optional]
            The channel to connect to. If a channel is not specified, an attempt to join the voice channel you are in
            will be made.
        This command also handles moving the bot to different channels.
        """
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                embed = discord.Embed(title="", description="No channel to connect. Please call `/connect` from a voice channel.", color=0xff0000)
                await ctx.send(embed=embed)
                raise InvalidVoiceChannel('No channel to connect. Please either specify a valid channel or connect one.')

        vc = ctx.voice_client

        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Moving to channel: <{channel}> timed out.')
        else:
            try:
                vc = await channel.connect()
                vc.play(discord.FFmpegPCMAudio(source=source.welcome), after=None)
            except asyncio.TimeoutError:
                raise VoiceConnectionError(f'Connecting to channel: <{channel}> timed out.')
         
        embed = discord.Embed(title=f"connectting to `{channel}` voice_channel...",color=0x73bbff)
        await ctx.send(embed=embed)

    @commands.command(name='play', aliases=['p','PLAY','P'], description="streams music")
    async def play_(self, ctx, *, search: str):
        """Request a song and add it to the queue.
        This command attempts to join a valid voice channel if the bot is not already in one.
        Uses YTDL to automatically search and retrieve a song.
        Parameters
        ------------
        search: str [Required]
            The song to search and retrieve using YTDL. This could be a simple search, an ID or URL.
        """
        if (ctx.channel.id in playchannel) or enable_special_playchannel == False :

            await ctx.typing()

            vc = ctx.voice_client

            if not vc:
                await ctx.invoke(self.connect_)
                time.sleep(4)###################################################@
                try :
                    await vc.stop()
                except Exception:
                    pass


            player = self.get_player(ctx)

            # If download is False, source will be a dict which will be used later to regather the stream.
            # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
            if "youtube.com/playlist?list=" in search :
                songs = yt_url_exploer.search(search)
                embed = discord.Embed(title="正在載入歌單...", description=f"預計載入時間:{round(0.7*len(songs), 2)}sec(s)", color=0xf6ff00)
                await ctx.send(embed=embed)

                if len(songs) >= 5:
                    embed = discord.Embed(title="歌單長度較長可能影響他人點歌權益", description="任何人均有權限跳過歌單內的歌", color=0xf6ff00)
                    await ctx.send(embed=embed)
                    flag = 1

                for song in songs :
                    source = await YTDLSource.create_source(ctx, song, loop=self.bot.loop, download=False, creat_Queued_message=False)
                    await asyncio.sleep(0.5)
                    if source != False :
                        await player.queue.put(queue_exploer.Prioritize(2,source))
                        if flag == 1 :
                            try:
                                list_song[ctx.guild.id].append(source['webpage_url'])
                            except KeyError :
                                e = [source['webpage_url']]
                                list_song[ctx.guild.id] = e
                    else :
                        embed = discord.Embed(title="載入失敗", description=str(source["title"]) + "=>於黑名單中error code:[403]", color=0xf6ff00)
                        await ctx.send(embed=embed)
                embed = discord.Embed(title="", description=f"已從歌單載入{len(songs)}首歌!", color=0xf6ff00)
                await ctx.send(embed=embed)
                await ctx.invoke(self.queue_info)

            else :
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False, creat_Queued_message=True)
                if source != False :
                    await player.queue.put(queue_exploer.Prioritize(1, source))
        else :
            embed = discord.Embed(title="", description="Please request a song on the designated channel.", color=0xf6ff00)
            await ctx.send(embed=embed)

    @commands.command(name='pause', aliases=['stop'], description="pauses music")
    async def pause_(self, ctx):
        """Pause the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=0xf6ff00)
            return await ctx.send(embed=embed)
        elif vc.is_paused():
            return

        vc.pause()
        await ctx.message.add_reaction('⏸️')
        await ctx.send("Paused")

    @commands.command(name='resume', description="resumes music")
    async def resume_(self, ctx):
        """Resume the currently paused song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)
        elif not vc.is_paused():
            return

        vc.resume()
        await ctx.message.add_reaction('⏯️')
        await ctx.send("Resuming")

    @commands.command(name='skip', description="skips to next song in queue")
    async def skip_(self, ctx):
        """Skip the song."""
        vc = ctx.voice_client
        voter = ctx.message.author

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=0xf6ff00)
            return await ctx.send(embed=embed)

        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return

        if voter == vc.source.requester :
            try :
                if vc.source.web_url in banned_song[ctx.guild.id]:
                    banned_song[ctx.guild.id].remove(vc.source.web_url)
            except KeyError:
                pass
            try :
                if vc.source.web_url in list_song[ctx.guild.id]:
                    list_song[ctx.guild.id].remove(vc.source.web_url)
            except KeyError :
                pass
            await ctx.message.add_reaction('⏭')
            self.totalvotes.clear()
            vc.stop()

        elif ctx.guild.id in filter_skip:
            if vc.source.web_url in banned_song[ctx.guild.id]:
                banned_song[ctx.guild.id].remove(vc.source.web_url)
            try :
                if vc.source.web_url in list_song[ctx.guild.id]:
                    list_song[ctx.guild.id].remove(vc.source.web_url)
            except KeyError:
                pass
            await ctx.message.add_reaction('⏭')
            self.totalvotes.clear()
            vc.stop()
            embed = discord.Embed(title="執行身分:[CORN_filter系統]", description="/skip", color=0x73d7ff)
            await ctx.send(embed=embed)

        elif ctx.guild.id in list_skip:
            if vc.source.web_url in list_song[ctx.guild.id]:
                list_song[ctx.guild.id].remove(vc.source.web_url)
            await ctx.message.add_reaction('⏭')
            self.totalvotes.clear()
            vc.stop()
            embed = discord.Embed(title="執行身分:[CORN_music_list系統]", description="/skip", color=0x73d7ff)
            await ctx.send(embed=embed)

        elif ctx.message.author.id in owner_id :
            await ctx.message.add_reaction('⏭')
            self.totalvotes.clear()
            vc.stop()
            embed = discord.Embed(title="執行身分:[系統管理員]", description="/skip", color=0x73d7ff)
            await ctx.send(embed=embed)

        elif voter not in self.totalvotes :
            self.totalvotes.append(voter)
            total_votes = len(self.totalvotes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭')
                self.totalvotes.clear()
                vc.stop()
            else:
                await ctx.send('Skip vote added, currently at **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    
    @commands.command(name='remove', aliases=['rm'], description="removes specified song from queue")
    async def remove_(self, ctx, pos : int=None):
        """Removes specified song from queue"""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        if pos == None:
            player.queue._queue.pop()
        else:
            try:
                s = (player.queue._queue[pos-1]).item
                del player.queue._queue[pos-1]
                embed = discord.Embed(title="", description=f"Removed [{s['title']}]({s['webpage_url']}) [{s['requester'].mention}]", color=0xf200ff)
                await ctx.send(embed=embed)
                try :
                    if s['webpage_url'] in banned_song[ctx.guild.id]:
                        banned_song[ctx.guild.id].remove(s['webpage_url'])
                except KeyError :
                    pass

                try : 
                    if s['webpage_url'] in list_song[ctx.guild.id]:
                        list_song[ctx.guild.id].remove(s['webpage_url'])
                except KeyError :
                    pass
            except:
                embed = discord.Embed(title="", description=f'Could not find a track for "{pos}"', color=0xff0000)
                await ctx.send(embed=embed)
    
    @commands.command(name='clear', aliases=['clr','fs','FS'], description="clears entire queue")
    async def clear_(self, ctx):
        """Deletes entire queue of upcoming songs."""

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        player.queue._queue.clear()
        try :
            del list_song[ctx.guild.id]
        except KeyError:
            pass
        try :
            del banned_song[ctx.guild.id]
        except KeyError :
            pass
        await ctx.message.add_reaction('💣')
        await ctx.send('**Cleared**')

    @commands.command(name='queue', aliases=['q', 'playlist', 'que'], description="shows the queue")
    async def queue_info(self, ctx, page :int=1):
        """Retrieve a basic queue of upcoming songs."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)
        if player.queue.empty():
            embed = discord.Embed(title="", description="queue is empty", color=0xf6ff00)
            return await ctx.send(embed=embed)

        seconds = vc.source.duration % (24 * 3600) 
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dh %02dm %02ds" % (hour, minutes, seconds)
        else:
            duration = "%02dm %02ds" % (minutes, seconds)

        total_len = int(len(player.queue._queue)) // 10
        page -= 1

        if page < 0:
            embed = discord.Embed(title="", description="queue <page:必須為不等於0之正數>", color=0xf6ff00)
            await ctx.send(embed=embed)

        elif page <= total_len :
        
            q_start = page*10
            e_color = 0x00eaff
            loop_mod = ""
            if ctx.guild.id in loop_list :
                loop_mod = "\nloop mod : ON"
                e_color = 0x00ff33

            # Grabs the songs in the queue...
            upcoming = list(itertools.islice(queue_exploer.queue_expr(player.queue._queue), q_start, (q_start+10)))
            fmt = '\n'.join(f"`{(upcoming.index(_)) + 1 + q_start}.` [{_['title']}]({_['webpage_url']}) | `Requested by: {_['requester']}`\n" for _ in upcoming)
            fmt = f"\n__Now Playing__:\n[{vc.source.title}]({vc.source.web_url}) | ` {duration} Requested by: {vc.source.requester}`\n\n__Up Next:__\n" + fmt +f"{loop_mod}" +f"\n**{len(player.queue._queue)} songs in queue**"
            embed = discord.Embed(title=f'Queue for {ctx.guild.name}', description=fmt, color=e_color)
            embed.set_footer(text=f"page:{page+1}/{total_len+1}", icon_url=ctx.author.avatar.url)

            await ctx.send(embed=embed)
        
        else :
            embed = discord.Embed(title="", description="queue <page: out of range>", color=0xf6ff00)
            await ctx.send(embed=embed)
            
    @commands.command(name='nowplaying', aliases=['playing'], description="shows the current playing song")
    async def now_playing_(self, ctx):
        """Display information about the currently playing song."""
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=0xf6ff00)
            return await ctx.send(embed=embed)
        
        seconds = vc.source.duration % (24 * 3600) 
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if hour > 0:
            duration = "%dhours, %dminutes, %dseconds" % (hour, minutes, seconds)
        else:
            duration = "%dminutes, %dseconds" % (minutes, seconds)

        embed = (discord.Embed(title='Now playing',
                               description=f'```css\n{vc.source.title}\n```',
                               color=0x73d7ff)
                 .add_field(name='Duration', value=duration)
                 .add_field(name='Requested by', value=vc.source.requester.mention)
                 .add_field(name='Uploader', value=f'[{vc.source.uploader}]({vc.source.uploader_url})')
                 .add_field(name='URL', value=f'[Click]({vc.source.web_url})')
                 .set_thumbnail(url=vc.source.thumbnail))
        embed.set_author(icon_url=self.bot.user.avatar.url, name=f"CORN Studio _Music")
        await ctx.send(embed=embed)

    @commands.command(name='volume', aliases=['vol', 'v'], description="changes Kermit's volume")
    async def change_volume(self, ctx, *, vol: float=None):
        """Change the player volume.
        Parameters
        ------------
        volume: float or int [Required]
            The volume to set the player to in percentage. This must be between 1 and 100.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I am not currently connected to voice channel", color=0xff0000)
            return await ctx.send(embed=embed)
        
        if not vol:
            embed = discord.Embed(title="", description=f"🔊 **{(vc.source.volume)*100}%**", color=0x00ff00)
            return await ctx.send(embed=embed)

        if not 0 < vol < 101:
            embed = discord.Embed(title="", description="Please enter a value between 1 and 100", color=0xf6ff00)
            return await ctx.send(embed=embed)

        player = self.get_player(ctx)

        if vc.source:
            vc.source.volume = vol / 100

        player.volume = vol / 100
        embed = discord.Embed(title="", description=f'**`{ctx.author}`** set the volume to **{vol}%**', color=0x00ff00)
        await ctx.send(embed=embed)

    @commands.command(name='disconnect', aliases=["d", "leave"], description="stops music and disconnects from voice")
    async def leave_(self, ctx):
        """Stop the currently playing song and destroy the player.
        !Warning!
            This will destroy the player assigned to your guild, also deleting any queued songs and settings.
        """
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        embed = discord.Embed(title="disconnect...",color=0x232323)
        await ctx.send(embed=embed)
        

        await self.cleanup(ctx.guild)

    @commands.command(name='loop', description="loop now playing song list.")
    async def loop_(self, ctx):

        player = self.get_player(ctx)
        vc = ctx.voice_client
        if not player.queue.empty() :
            upcoming = list(itertools.islice(queue_exploer.queue_expr(player.queue._queue), 0, len(player.queue._queue)))

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=0xf6ff00)
            return await ctx.send(embed=embed)

        if ctx.guild.id not in loop_list:
            loop_list.append(ctx.guild.id)
            embed = discord.Embed(title="turn on loop mod", description=f"type /break to break the loop", color=0x00ff00)
            await ctx.send(embed=embed)
            if player.queue.empty() or upcoming[-1]["webpage_url"] != vc.source.web_url :
                s = await YTDLSource.create_source(ctx, vc.source.web_url, loop=self.bot.loop, download=False, creat_Queued_message=False)
                await player.queue.put(queue_exploer.Prioritize(3,s))
        else :
            embed = discord.Embed(title="you have already turn on loop mod", description=f"type /break to break the loop", color=0xf6ff00)
            await ctx.send(embed=embed)
    

    @commands.command(name='break', description="break play loop.")
    async def break_(self, ctx):

        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            embed = discord.Embed(title="", description="I'm not connected to a voice channel", color=0xff0000)
            return await ctx.send(embed=embed)

        if not vc or not vc.is_playing():
            embed = discord.Embed(title="", description="I am currently not playing anything", color=0xf6ff00)
            return await ctx.send(embed=embed)

        if ctx.guild.id in loop_list:
            loop_list.remove(ctx.guild.id)
            embed = discord.Embed(title="turn off loop mod", description=f"", color=0x00ff00)
            await ctx.send(embed=embed)
        else :
            embed = discord.Embed(title="you have already turn off loop mod", description=f"type /loop to loop the play list", color=0xf6ff00)
            await ctx.send(embed=embed)

    #===================================================================================================STT

async def setup(bot):
    await bot.add_cog(Music(bot))
