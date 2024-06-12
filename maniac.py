import discord
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import random

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intens = discord.Intents.default()
    intens.message_content = True
    client = discord.Client(intents=intens)

    voice_clients = {}  # Dictionary to hold voice clients per guild
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)
    ffmpeg_options = {'options': '-vn'}

    @client.event
    async def on_ready():
        print(f'{client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return  # Ignore messages sent by the bot itself

        if message.content.startswith('?play'):
            try:
                # Check if the author is in a voice channel
                if message.author.voice is None:
                    await message.channel.send("You are not connected to a voice channel.")
                    return

                # Connect to the voice channel of the message author
                voice_client = await message.author.voice.channel.connect()
                voice_clients[message.guild.id] = voice_client

            except Exception as e:
                print(e)
                return

            try:
                url = message.content.split()[1]

                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, ytdl.extract_info, url, {'download': False})

                if 'entries' in data:
                    # Playlist handling
                    playlist = []
                    for entry in data['entries']:
                        song = entry['url']
                        playlist.append(song)

                    # Shuffle the playlist
                    random.shuffle(playlist)

                    # Start playing the shuffled playlist
                    await play_song(message, playlist)

                else:
                    song = data['url']
                    player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
                    voice_clients[message.guild.id].play(player)
                    await message.channel.send(f"Now playing: {data['title']}")

            except yt_dlp.DownloadError as e:
                if 'Video unavailable' in str(e):
                    await message.channel.send("This video is unavailable due to a copyright claim.")
                else:
                    await message.channel.send(f"An error occurred: {e}")
                    voice_clients[message.guild.id].stop()
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")
                voice_clients[message.guild.id].stop()

        elif message.content.startswith('?pause'):
            try:
                voice_clients[message.guild.id].pause()
                await message.channel.send("Playback paused.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif message.content.startswith('?resume'):
            try:
                voice_clients[message.guild.id].resume()
                await message.channel.send("Playback resumed.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif message.content.startswith('?skip'):
            try:
                voice_clients[message.guild.id].stop()
                await message.channel.send("Skipped to the next song.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif message.content.startswith('?stop'):
            try:
                voice_clients[message.guild.id].stop()
                await voice_clients[message.guild.id].disconnect()
                del voice_clients[message.guild.id]
                await message.channel.send("Playback stopped.")
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

        elif message.content.startswith('?shuffle'):
            try:
                # Check if there's a playlist currently playing
                if message.guild.id in voice_clients and voice_clients[message.guild.id].is_playing():
                    # Get the current playlist
                    current_playlist = []
                    for entry in voice_clients[message.guild.id].source.playlist:
                        current_playlist.append(entry.url)

                    # Shuffle the current playlist
                    random.shuffle(current_playlist)

                    # Clear the current playlist
                    voice_clients[message.guild.id].stop()

                    # Start playing the shuffled playlist
                    await play_song(message, current_playlist)

                    await message.channel.send("Shuffled the playlist!")

                else:
                    await message.channel.send("No playlist is currently playing.")

            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

    async def play_song(message, playlist):
        for song in playlist:
            player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
            voice_clients[message.guild.id].play(player)
            await message.channel.send(f"Now playing: {song}")
            while voice_clients[message.guild.id].is_playing():
                await asyncio.sleep(1)

    client.run(TOKEN)

if __name__ == "__main__":
    run_bot()
