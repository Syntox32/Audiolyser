import time
import spidev
import sys
import fcntl
import spidev
import wave
import os
import argparse
import socket
import threading
import math
import base64
import gzip

import alsaaudio as aa
import numpy as np
import fft

CHUNK_SIZE = 2048

class LEDDevice():
	def __init__(self, numleds, x=0, d=0):
		"""
		Initalize an LEDDevice with the number of LEDs to control
		
		Parameter x and d are representative of the location of the device:
			/dev/spidev{bus=x}.{device=d}

		Credits to Doceme for the py-spidev project
		https://github.com/doceme/py-spidev

		Credits to Scott Gibson for the gamma correction
		https://github.com/scottjgibson/PixelPi/blob/master/pixelpi.py#L604
		"""
		self._spi = spidev.SpiDev()
		self._open = False
		self.x = x
		self.d = d
		self.chip_name = "WS2801"
		self.brightness = 1.0
		self.bits_per_pixel = 3
		self.num_leds = numleds
		self.gamma_table = bytearray(256)
		for i in range(256):
			self.gamma_table[i] = int(pow(float(i) / 255.0, 2.5) * 255.0)

	def open(self, speed=1000000):
		"""
		Open an spi device
		"""
		try:
			print "Creating LED device for chip:", self.chip_name
			self._spi.open(self.x, self.d)
			self._spi.max_speed_hz = speed
			self._spi.bits_per_word = 8
			self._spi.mode = 2 # SPI_CPOL - high bit order
 			self._open = True
			print "SPI Interface ready -> /dev/spidev{0}.{1}".format(str(self.x), str(self.d))
			print "SPI Mode:", str(self._spi.mode)
			print "SPI Bits Per Word:", str(self._spi.bits_per_word)
			print "SPI Max Speed: {0}Hz ({1}KHz)".format(str(self._spi.max_speed_hz), str(self._spi.max_speed_hz / 1000))
			return True
		except IOError as e:
			print "IO Error opening SPI Device:", e
			return False
		except Exception as e:
			print "Error opening SPI Device:", e
			return False

	def write(self, intarray):
		"""
		Write a byte array to the device

		The WS2801 chip uses simple 24-bit RGB color for each LED
		A byte-array should be like this: rgbrgbrgr...
		"""
		self._spi.writebytes(intarray)

	def write_gc(self, intarray):
		"""
		Write a gamma corrected array of rgb colors
		"""
		self._spi.writebytes([self.gamma_table[intarray[i]] for i in range(0, len(intarray))])

	def write_gc_wb(self, intarray, brightness=1.0):
		"""
		Write a gamma corrected array of rgb colors with shitty brightness
		"""
		self._spi.writebytes([
			self.gamma_table[int(intarray[i] * brightness)] for i in range(0, len(intarray))])

	def all_on(self):
		"""
		Turn on all the LEDS
		"""
		self._spi.writebytes([0xFF for _ in range(0, self.num_leds * self.bits_per_pixel)])

	def all_off(self):
		"""
		Turn of all the LEDs
		"""
		self._spi.writebytes([0x00 for _ in range(0, self.num_leds * self.bits_per_pixel)])

	def close(self):
		"""
		Close the spi device and turn off all the lights
		"""
		print "Closing SPI interface.."
		if self._spi.open:
			self.all_off()
			self._spi.close()
		self.open = False

class LEDServer:
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.running = False
		self.connected = False
		self.connection = None
		self._buffer_size = 1024
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # TEMP

	def start(self):
		print "Starting server.."
		print "Warning: Running using option SO_REUSEADDR"
		self._socket.bind((self.host, self.port))
		self.running = True
		print "Running on: {0}:{1}".format(self.host, str(self.port))

	def listen(self):
		if self.connected:
			print "There is already an existing connection."
			return
		print "Listening.."
		self._socket.listen(1)
		(conn, addr) = self._socket.accept()
		self.connection = conn
		self.connected = True
		print "Accepted connection from: {0}:{1}".format(addr[0], str(addr[1]))
	
	def wait_command(self, command, resp=True):
		r = self.connection.recv(self._buffer_size)
		while r != command:
			r = self.connection.recv(self._buffer_size)
		print "Recieved command:", command
		self.connection.sendall(str(resp))

	def send_command(self, command):
		self.connection.sendall(command)
		r = self.connection.recv(self._buffer_size)
		if r == command:
			print "Command '{0}' returned True".format(command)
			return True
		else:
			print "Command '{0}' returned False".format(command)
			return False
	
	def send(self, data):
		self.connection.sendall(data)

	def recv(self):
		return self.connection.recv(self._buffer_size)

	def disconnect(self):
		if self.connected:
			self.connection.close()
			self.connected = False
			print "Disconnected from client.."

	def close(self):
		print "Closing server.."
		if self.running:
			if self.connected:
				self.connection.close()
				self.connected = False
			self._socket.close()
			self.running = False

def main():
	"""
	Server for the RPi LED thing
	"""
	parser = argparse.ArgumentParser(description='Server for RPi LEDs')
	parser.add_argument('-p', '--port', type=int, default=1337)
	parser.add_argument('-i', '--host-address', required=False)
	parser.add_argument('-s', '--song-path', required=True)
	args = parser.parse_args()

	host = ''
	if args.host_address is None:
		host = socket.gethostbyname(socket.gethostname())
	else:
		host = args.host_address
	
	port = args.port
	song = os.path.abspath(args.song_path)
	song_name = os.path.basename(song)

	server = LEDServer(host, port)
	server.start()
	server.listen()

	spi = LEDDevice(32, 0, 0)
	spi.open()

	server.send_command("amazing")

	spi.close()
	server.close()

	sys.exit(0)

	print "Playing:", song_name

	print host
	print str(port)
	print song
	print song_name

	cache = recieve_cache()
	filename = save_cache_to_file(cache)
	print "FILENAME: " + filename
	limits = read_cache(filename)
	
	m = np.matrix(limits)
	print "max: ", m.max()
	print "mean:", m.mean()
	print "newmin: ", m.mean() - (m.max() - m.mean())

	LEDS = []
	for i in range(0, 32):
		l = []
		for _ in range(0, i):
			l.extend([GAMMA[255],GAMMA[255],GAMMA[255]])
		for _ in range(0, 32 - i):
			l.extend([0x00, 0x00, 0x00])
		LEDS.append(l)

	print "Listenting for things"

	it = 1
	i = 0
	prev = 0

	# Create a dummy stream for syncing the audio
	# Seems to work better then expected
	musicfile = wave.open("downtheroad.wav", 'r')
	sample_rate = musicfile.getframerate()
	num_channels = musicfile.getnchannels()
	output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
	output.setchannels(num_channels)
	output.setrate(sample_rate)
	output.setformat(aa.PCM_FORMAT_S16_LE)
	output.setperiodsize(CHUNK_SIZE)

	data = musicfile.readframes(CHUNK_SIZE)
	while data != '':
		output.write(data)
		it += 1
		if it >= 31:
			it = 0
		l = (int((limits[i][2] - 6) * 3)) + 1
		i += 1
		write_spi(LEDS[l][::-1])
		prev = l

		data = musicfile.readframes(CHUNK_SIZE)

	print "Finish up, closing down.."
	server.close()

if __name__ == '__main__':
	print "So far so good.."
	try:
		main()
	except KeyboardInterrupt:
		print "losing down.."

"""
def write_cache(filename):
	print "Caching file: ", filename
	d = wave.open(os.path.abspath(filename))
	sample_rate = d.getframerate()
	data = d.readframes(CHUNK_SIZE)
	limits = []
	while data != '':
		limits.append(fft.calculate_levels(
			data, CHUNK_SIZE, sample_rate, _FREQ_LIMITS, _GIOP_LEN, 2))
		data = d.readframes(CHUNK_SIZE)
	cache_filename = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
	print "Creating cache file: ", cache_filename
	with gzip.open(cache_filename, 'wb') as f:
		for i in range(0, len(limits)):
			line = ",".join([str(limits[i][j]) for j in range(0, len(limits[i]))]) + "\n"
			f.write(line)
	print "Length of limits: ", str(len(limits))
	return limits

def read_cache(filename):
	cache_filename = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
	print "Reading cache: ", os.path.splitext(filename)[0] + ".cache"
	limits = []
	with gzip.open(cache_filename, 'rb') as f:
		line = f.readline()
		while line != '' or line == '\n':
			line = line.replace('\n', '').split(',')
			limits.append([float(line[i]) for i in range(0, len(line))])
			line = f.readline()
	print "Cache reading completed: " + str(len(limits)) + " entries read"
	return limits

def recieve_cache():
	print "Listening.."
	SOCKET.connect((HOST, PORT))
	print "Connected to: ", (HOST, PORT)
	data = SOCKET.recv(SOCKET_CHUNK_SIZE)
	buff = ""
	while data != '':
		buff += data
		data = SOCKET.recv(SOCKET_CHUNK_SIZE)
	print "Length of recv: ", len(buff)
	SOCKET.close()
	return buff # return base64 encoded gzip data

def save_cache_to_file(raw_base64_cache):
	name = raw_base64_cache.split(':')[0]
	data = raw_base64_cache.split(':')[1]
	cache_filename = name + ".cache"
	cache_path = os.path.abspath(cache_filename)
	decode_cache = base64.b64decode(data)
	with open(cache_path, 'wb') as f:
		f.write(decode_cache)
	print "Saved cache to: ", cache_path
	return cache_filename
"""
