import wave
import sys
import fft
import math
import time
import gzip
import base64
import socket

import pyaudio as pa
import numpy as np
import ntpath as nt

from os.path import abspath, basename, splitext, isfile
from argparse import ArgumentParser
from cachehandler import Cache

class LEDClient:
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.connected = False
		self.buffer_size = 1024
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	def connect(self):
		print "Connecting to: {0}:{1}".format(self.host, str(self.port))
		self._socket.connect((self.host, self.port))
		self.connected = True
		print "Connection accepted.."

	def wait_command(self, command, resp=True):
		r = self._socket.recv(self.buffer_size)
		while r != command:
			r = self._socket.recv(self.buffer_size)
		self._socket.sendall(str(resp))
		return r

	def send_command(self, command):
		print "sending command"
		self._socket.sendall(command)
		r = self._socket.recv(self.buffer_size)
		if r == 'True':
			return True
		elif r == 'False':
			return False
		else:
			print "no quantum computers allowed, please"
			return False
	
	def send(self, data):
		self._socket.sendall(data)

	def recv(self):
		return self._socket.recv(self.buffer_size)

	def close(self):
		print "Closing client.."
		if self.connected:
			self._socket.close()

class LimitsHandler():
	def __init__(self):
		self.chunk_size = 2048
		self.max_freq = 15000
		self.min_freq = 20
		self.gpio_len = 5 # number of bars
		self.n_channnels = 2 # use 1 if mono
		self.freq_limits = [ [20, 1000], [1000, 5000], [5000, 7000], [7000, 10000], [10000, 15000] ]

	def generate_limits(self, wave_file):
		sample_rate = wave_file.getframerate()
		data = wave_file.readframes(self.chunk_size)
		limits = []
		while data != '':
			limits.append(fft.calculate_levels(
				data, self.chunk_size, sample_rate, self.freq_limits, self.gpio_len, self.n_channnels))
			data = wave_file.readframes(self.chunk_size)
		return limits

def norm(val, minval, maxval):
	return (val - minval) / (maxval - minval)

def play(client, song, song_name, cache_name, force_cache):
	limits = LimitsHandler()
	
	with open(song, 'rb') as f:
		d = wave.open(f)
		levels = limits.generate_limits(d)
		Cache.write_cache(levels, cache_name, song, limits.chunk_size)
		succ = Cache.transfer_cache(client, cache_name, force_cache)

	p = pa.PyAudio()
	d = wave.open(song)

	stream = p.open(
		format = p.get_format_from_width(d.getsampwidth()),
		channels = d.getnchannels(),
		rate = d.getframerate(),
		output = True)

	sample_rate = d.getframerate()
	data = d.readframes(limits.chunk_size)

	try:
		client.wait_command("go", True)
		print "Playing:", song_name

		while data != '':
			stream.write(data)
			data = d.readframes(limits.chunk_size)
	except KeyboardInterrupt:
		print "KeyboardInterrupt: Closing streams.."
	except IOError:
		print "Lost connection to server, closing streams.."
	except:
		print "fuck if i know:", sys.exc_info()[0]
	finally:
		stream.stop_stream()
		stream.close()
		p.terminate()

	print "Done, streams closed.."
	print "Finished playing:", song_name

def main():
	"""
	Client for the RPi LED thing
	"""
	parser = ArgumentParser(description='Client for RPi LEDs')
	parser.add_argument('-p', '--port', type=int, default=1337)
	parser.add_argument('-i', '--host-address', required=True)
	parser.add_argument('-s', '--song-path', required=True)
	parser.add_argument('-f', '--force-cache', action='store_true')
	#parser.add_argument('-c', '--chunk-sync', action='store_true') # default
	# TODO: Add verbose argument
	args = parser.parse_args()

	port = args.port
	host = args.host_address
	song = abspath(args.song_path)
	song_name = basename(song)
	cache_name = Cache.get_cache_path(song)
	force_cache = args.force_cache
	# chunk_sync = True #args.chunk_sync
	
	client = LEDClient(host, port)
	client.connect()
	
	try:
		play(client, song, song_name, cache_name, force_cache)
	except Exception as e:
		print "Error:", e
		
	print "Closing connection.."
	client.close()
	
if __name__ == '__main__':
	main()