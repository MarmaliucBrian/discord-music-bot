import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    print(f"TOKEN: {TOKEN}")  # Debugging output to check the value of TOKEN
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents)

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    youtube_playlist_url = youtube_base_url + 'playlist?list='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn -filter:a "volume=0.25"'}

    # Flag to track if a skip operation is in progress
    skip_in_progress = {}

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    async def play_next(ctx):
        try:
            if queues[ctx.guild.id]:
                link = queues[ctx.guild.id].pop(0)
                await play(ctx, link=link)
            else:
                await ctx.send("Queue is empty!")
        except Exception as e:
            print(f"Error in play_next: {e}")

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    @client.command(name="queue")
    async def queue(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")

    @client.command(name="skip")
    async def skip(ctx):
        try:
            if ctx.guild.id in skip_in_progress and skip_in_progress[ctx.guild.id]:
                await ctx.send("Already skipping, please wait.")
                return

            skip_in_progress[ctx.guild.id] = True

            if voice_clients[ctx.guild.id]:
                voice_clients[ctx.guild.id].stop()
                await ctx.send("Skipped the current song.")
                await play_next(ctx)
            else:
                await ctx.send("No song is currently playing!")

            skip_in_progress[ctx.guild.id] = False

        except Exception as e:
            await ctx.send("Failed to skip the current song.")
            print(e)

    @client.command(name="playlist")
    async def playlist(ctx, *, url):
        try:
            if youtube_playlist_url in url:
                playlist_id = url.split('list=')[1]
                data = ytdl.extract_info(url, download=False)
                songs = [entry['webpage_url'] for entry in data['entries'] if 'webpage_url' in entry]

                if ctx.guild.id not in queues:
                    queues[ctx.guild.id] = []

                if not voice_clients[ctx.guild.id].is_playing() and not voice_clients[ctx.guild.id].is_paused():
                    queues[ctx.guild.id].extend(songs)
                    await ctx.send(f"Added {len(songs)} songs from the playlist to the queue!")
                    await play_next(ctx)
                else:
                    queues[ctx.guild.id].extend(songs)
                    await ctx.send(f"Added {len(songs)} songs from the playlist to the queue!")

            else:
                await ctx.send("Invalid YouTube playlist URL.")

        except Exception as e:
            await ctx.send("Error adding playlist to queue.")
            print(e)

    @client.command(name="join")
    async def join(ctx):
        try:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                voice_client = await channel.connect()
                voice_clients[ctx.guild.id] = voice_client
            else:
                await ctx.send("You are not connected to a voice channel.")
        except Exception as e:
            await ctx.send(f"Failed to join the voice channel: {e}")

    @client.command(name="play")
    async def play(ctx, *, link=None):
        try:
            voice_client = voice_clients.get(ctx.guild.id)
            if not voice_client:
                voice_client = await ctx.author.voice.channel.connect()
                voice_clients[ctx.guild.id] = voice_client

            if link:
                if youtube_base_url not in link:
                    query_string = urllib.parse.urlencode({
                        'search_query': link
                    })
                    content = urllib.request.urlopen(
                        youtube_results_url + query_string
                    )
                    search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                    link = youtube_watch_url + search_results[0]

                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

                if 'entries' in data:
                    songs = [entry['url'] for entry in data['entries']]
                else:
                    songs = [data['url']]

                for song in songs:
                    player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                    voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))

        except Exception as e:
            print(e)

    client.run(TOKEN)

