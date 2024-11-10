# AudioHandler.py
import asyncio
import discord
import pyaudio
import threading
import sys

# Constants
CHUNK = 960  # Number of samples per frame (20ms of 48000Hz audio)
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 2  # Stereo
RATE = 48000  # 48kHz
EXPECTED_DEVICES = {
    'input': 'WhiteHole 2ch',   # Replace with your actual input device name
    'output': 'BlackHole 2ch'   # Replace with your actual output device name
}

class PyAudioInputStream(discord.AudioSource):
    def __init__(self, input_device_name='WhiteHole 2ch', channels=2, rate=48000, chunk=960):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.chunk = chunk
        self.channels = channels
        self.rate = rate
        self.input_device_name = input_device_name

        # Find the input device index
        self.input_device_index = self.get_device_index(input_device_name, input=True)
        if self.input_device_index is None:
            raise ValueError(f"Input device '{input_device_name}' not found.")

        # Open the input stream
        self.stream = self.p.open(format=FORMAT,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  input_device_index=self.input_device_index,
                                  frames_per_buffer=self.chunk)

        self.loop = asyncio.get_event_loop()
        self.running = True
        self.buffer = asyncio.Queue()

        # Start a separate thread to read audio data
        self.thread = threading.Thread(target=self.read_audio)
        self.thread.start()

    def get_device_index(self, name, input=True):
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if name.lower() in device_info['name'].lower():
                if input and device_info['maxInputChannels'] > 0:
                    return i
                elif not input and device_info['maxOutputChannels'] > 0:
                    return i
        return None

    def read_audio(self):
        while self.running:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                # Put the data into the asyncio queue
                asyncio.run_coroutine_threadsafe(self.buffer.put(data), self.loop)
            except Exception as e:
                print(f"Error reading audio: {e}", file=sys.stderr)
                self.running = False

    def read(self):
        # This method should return 20ms of PCM data
        try:
            data = self.buffer.get_nowait()
            return data
        except asyncio.QueueEmpty:
            return b'\x00' * self.chunk * self.channels * 2  # Silence

    def is_opus(self):
        return False  # We're sending PCM data; discord.py will handle Opus encoding

    def cleanup(self):
        self.running = False
        self.thread.join()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

class PyAudioOutputStream:
    def __init__(self, voice_client, output_device_name='BlackHole 2ch', channels=2, rate=48000, chunk=960):
        self.voice_client = voice_client
        self.p = pyaudio.PyAudio()
        self.chunk = chunk
        self.channels = channels
        self.rate = rate
        self.output_device_name = output_device_name

        # Find the output device index
        self.output_device_index = self.get_device_index(output_device_name, input=False)
        if self.output_device_index is None:
            raise ValueError(f"Output device '{output_device_name}' not found.")

        # Open the output stream
        self.stream = self.p.open(format=FORMAT,
                                  channels=self.channels,
                                  rate=self.rate,
                                  output=True,
                                  output_device_index=self.output_device_index,
                                  frames_per_buffer=self.chunk)

        # Queue to receive audio data
        self.audio_queue = asyncio.Queue()

        self.loop = asyncio.get_event_loop()
        self.running = True

        # Start a separate thread to play audio data
        self.thread = threading.Thread(target=self.play_audio)
        self.thread.start()

        # Attach the audio queue to the voice client (requires voice client support)
        self.voice_client.audio_queue = self.audio_queue

    def get_device_index(self, name, input=False):
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if name.lower() in device_info['name'].lower():
                if input and device_info['maxInputChannels'] > 0:
                    return i
                elif not input and device_info['maxOutputChannels'] > 0:
                    return i
        return None

    async def receive_audio_packet(self, data):
        await self.audio_queue.put(data)

    def play_audio(self):
        while self.running:
            try:
                data = self.loop.run_until_complete(self.audio_queue.get())
                self.stream.write(data)
            except Exception as e:
                print(f"Error playing audio: {e}", file=sys.stderr)
                self.running = False

    def stop(self):
        self.running = False
        self.thread.join()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
