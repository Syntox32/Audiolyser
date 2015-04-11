import os
import sys
import time
import spidev
import fcntl
import spidev
import threading
import random
from timeit import Timer

import wave, sys, fft, math, gzip, base64, socket
import alsaaudio as aa
import numpy as np
import ntpath as nt

from os.path import abspath, basename, splitext, isfile
from argparse import ArgumentParser
from cachehandler import Cache

class LEDDevice():
	def __init__(self, numleds, x=0, d=0):
		"""
		Initalize an LEDDevice with the number of LEDs to control
		
		Parameter x and d are representative of the location of the device:
			/dev/spidev{bus=x}.{device=d}

		Credits to Doceme for the spidev python port
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
		self.buffer_size = 1024
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# only use REUSEADDR while debugging pls, also don't use drugs, kids
		self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
		r = self.connection.recv(self.buffer_size)
		while r != command:
			r = self.connection.recv(self.buffer_size)
		# print "Recieved command:", command
		self.connection.sendall(str(resp))
		return r

	def send_command(self, command):
		#print "sending command"
		self.connection.sendall(command)
		r = self.connection.recv(self.buffer_size)
		if r == 'True':
			return True
		elif r == 'False':
			return False
		else:
			print "no quantum computers allowed"
			return False
	
	def send(self, data):
		self.connection.sendall(data)

	def recv(self):
		return self.connection.recv(self.buffer_size)

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

def norm(val, minval, maxval):
	return (val - minval) / (maxval - minval)

def play(server, spi, channel):
	fname = Cache.recieve_cache(server)
	(sr, c, chunk, levels) = Cache.read_cache(fname)

	song = abspath(fname)
	song_name = basename(fname)
	chunk_size = 2048

	LEDS = []
	for i in range(0, 32):
		l = []
		for _ in range(0, i):
			l.extend([255,0,0])
		for _ in range(0, 32 - i):
			l.extend([0, 0, 0])
		LEDS.append(l)

	it = 1
	i = 0
	l = 0
	prev = 0

	m = np.matrix(levels)
	lvlmax = m.max()
	lvlmean =  m.mean()
	lvllow = m.mean() - (m.max()-m.mean())

	# Create a dummy stream for syncing the audio
	# Seems to work better then expected
	sample_rate = sr
	num_channels = c
	output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
	output.setchannels(num_channels)
	output.setrate(sample_rate)
	output.setformat(aa.PCM_FORMAT_S16_LE)
	output.setperiodsize(chunk_size)

	data = chunk

	try:
		server.send_command("go")
		print "Playing:", song_name

		while data != '':
			output.write(data)
			it += 1
			# if it >= 31:
				# it = 0
			l = (int((levels[i][int(channel)] - 6) * 3)) + 1
			i += 1
			spi.write_gc(LEDS[l][::-1]) # norm(LEDS[l], lvllow, lvlmax))
			prev = l
	except KeyboardInterrupt:
		print "KeyboardInterrupt: Closing streams.."
	except IOError:
		print "Lost connection to the client, closing streams.."
	except:
		print "fuck if i know:", sys.exc_info()[0]
	finally:
		spi.all_off()

	print "Finished playing:", song_name

def main():
	"""
	Server for the RPi LED thing
	"""
	parser = ArgumentParser(description='Server for RPi LEDs')
	parser.add_argument('-p', '--port', type=int, default=1337)
	parser.add_argument('-i', '--host-address', required=False)
	parser.add_argument('-s', '--song-path', required=False)
	parser.add_argument('-c', '--channel', type=int, default=2)
	args = parser.parse_args()
	
	host = ''
	if args.host_address is None:
		host = socket.gethostbyname(socket.gethostname())
	else:
		host = args.host_address
	
	port = args.port

	server = LEDServer(host, port)
	server.start()
	server.listen()

	spi = LEDDevice(32, 0, 0)
	spi.open()

	try:
		play(server, spi, args.channel)
	except Exception as e:
		print "Error:", e

	spi.close()
	server.close()

if __name__ == '__main__':
	main()