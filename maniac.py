import discord
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv


def run_bot():
    load_dotenv()
    TOKEN = os.getenv('discord_token')
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    voice_clients = {}
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'options': '-vn'}

    @client.event
    async def on_ready():
        print(f'{client.user} has connected to Discord!')

    @client.event
    async def on_message(message):
        if message.author.bot:
            return

        if message.content.startswith('?play'):
            try:
                if message.author.voice and message.author.voice.channel:
                    channel = message.author.voice.channel
                    if message.guild.id not in voice_clients:
                        voice_client = await channel.connect()
                        voice_clients[message.guild.id] = voice_client
                    else:
                        voice_client = voice_clients[message.guild.id]

                    url = message.content.split()[1]
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
                    song = data['url']
                    player = discord.FFmpegPCMAudio(song, **ffmpeg_options)

                    if not voice_client.is_playing():
                        voice_client.play(player)
                    else:
                        await message.channel.send("Already playing a song. Please stop the current one first.")

                else:
                    await message.channel.send("You need to be in a voice channel to play music.")

            except Exception as e:
                print(e)
                await message.channel.send("An error occurred while trying to play the song.")

        if message.content.startswith('?pause'):
            try:
                if message.guild.id in voice_clients:
                    voice_clients[message.guild.id].pause()
                else:
                    await message.channel.send("Not connected to a voice channel.")
            except Exception as e:
                print(e)

        if message.content.startswith('?resume'):
            try:
                if message.guild.id in voice_clients:
                    voice_clients[message.guild.id].resume()
                else:
                    await message.channel.send("Not connected to a voice channel.")
            except Exception as e:
                print(e)

        if message.content.startswith('?stop'):
            try:
                if message.guild.id in voice_clients:
                    voice_clients[message.guild.id].stop()
                    await voice_clients[message.guild.id].disconnect()
                    del voice_clients[message.guild.id]
                else:
                    await message.channel.send("Not connected to a voice channel.")
            except Exception as e:
                print(e)

    client.run(TOKEN)


run_bot()
