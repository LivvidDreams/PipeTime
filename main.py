# main.py
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from AudioHandler import PyAudioInputStream, PyAudioOutputStream
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="~", intents=intents)

# Dictionary to keep track of audio streams per voice client
audio_streams = {}

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')

@bot.command(name='ft')
async def ft_command(ctx, action: str = None, sub_action: str = None):
    if action == "start" and sub_action == "call":
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client:
                await ctx.voice_client.move_to(channel)
            else:
                vc = await channel.connect()
                await ctx.send("Joining your voice channel...")

                try:
                    # Initialize input and output streams
                    input_stream = PyAudioInputStream(input_device_name='WhiteHole 2ch')
                    output_stream = PyAudioOutputStream(vc, output_device_name='BlackHole 2ch')

                    # Start a background task to handle sending audio
                    asyncio.create_task(send_audio(vc, input_stream))

                    # Store the streams in the dictionary
                    audio_streams[vc] = (input_stream, output_stream)

                    await ctx.send("Audio streaming started.")
                except ValueError as ve:
                    await ctx.send(str(ve))
        else:
            await ctx.send("You need to be in a voice channel for me to join.")

    elif action == "end" and sub_action == "call":
        if ctx.voice_client:
            vc = ctx.voice_client
            streams = audio_streams.get(vc)
            if streams:
                input_stream, output_stream = streams
                # Cleanup input stream
                input_stream.cleanup()
                # Cleanup output stream
                output_stream.stop()
                del audio_streams[vc]
            await vc.disconnect()
            await ctx.send("Leaving the voice channel and stopping audio streaming.")
        else:
            await ctx.send("I am not currently in a voice channel.")
    else:
        await ctx.send("Invalid command. Use `~ft start call` or `~ft end call`.")

async def send_audio(vc, input_stream):
    try:
        while vc.is_connected() and input_stream.running:
            data = input_stream.read()
            if data:
                # Send PCM data to Discord; discord.py handles Opus encoding
                vc.send_audio_packet(discord.AudioPacket(data))
            await asyncio.sleep(0)  # Yield control to the event loop
    except Exception as e:
        print(f"Error in send_audio: {e}")

def main():
    bot.run(TOKEN)

if __name__ == '__main__':
    main()
