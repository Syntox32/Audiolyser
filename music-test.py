import wave, sys, fft, math, gzip, base64, socket
import pyaudio as pa
import numpy as np
import ntpath as nt

from os.path import abspath, basename, splitext, isfile
from argparse import ArgumentParser

class Cache(object):
	@staticmethod
	def write_cache(limits, path):
		if limits is None:
			print "Warning: 'limits' is null"
		print "Creating cache file:", path
		with gzip.open(path, 'wb') as f:
			for i in range(0, len(limits)):
				f.write(",".join([str(limits[i][j]) for j in range(0, len(limits[i]))]) + "\n")

	@staticmethod
	def read_cache(path):
		limits = []
		print "Reading cache:", basename(path)
		with gzip.open(path, 'rb') as f:
			line = f.readline()
			while line != '' or line == '\n':
				line = line.replace('\n', '').split(',')
				limits.append([float(line[i]) for i in range(0, len(line))])
				line = f.readline()
		print "Cache reading completed: {0} entries read".format(str(len(limits)))
		return limits

	@staticmethod
	def transfer_cache(ledsocket, filename):
		ledsocket.send(filename)
		hascache = ledsocket.send_command("hascache")
		if hascache:
			print "Cache already exists.."
			return False
		else:
			print "Cache is needed.."
		print "Transfering cache:", filename
		with open(filename, 'rb') as f:
			data = f.read(ledsocket.buffer_size)
			ledsocket.send(data)
			l = len(data)
			while data != '':
				data = f.read(ledsocket.buffer_size)
				ledsocket.send(data)
				l += len(data)
			print "Sent {0} bytes".format(str(l))
		print "Cache transfered successfully"
		return True

	@staticmethod
	def recieve_cache(ledsocket):
		filename = ledsocket.recv()
		#TODO: basename behaves differently on windows and linux
		path = abspath(nt.basename(filename))
		exists = isfile(path)
		cmd = ledsocket.wait_command("hascache", exists)
		if exists == True:
			print "Cache already exists.."
			return path
		print "Cache does not exist, recieving cache.."
		with open(path, 'wb') as f:
			data = ledsocket.recv()
			l = len(data)
			while data != '':
				f.write(data)
				data = ledsocket.recv()
				l += len(data)
			print "Recieved {0} bytes".format(str(l))
		print "Recieved cache:", path
		return path

	@staticmethod
	def get_name_from_path(filepath):
		return splitext(basename(filename))[0] + ".cache"

	@staticmethod
	def get_cache_name(filename):
		return splitext(basename(filename))[0] + ".cache"

	@staticmethod
	def get_cache_path(filename):
		return abspath(splitext(basename(filename))[0] + ".cache")

	@staticmethod
	def check_cache_exists(filename):
		print "Checking if exist:", abspath(basename(filename))
		return isfile(abspath(basename(filename)))

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
		#print "Recieved command:", command
		self._socket.sendall(str(resp))
		return r

	def send_command(self, command):
		self._socket.sendall(command)
		r = self._socket.recv(self.buffer_size)
		if r == 'True':
			return True
		elif r == 'False':
			return False
		else:
			print "no quantum computers allowed"
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

def main():
	"""
	Client for the RPi LED thing
	"""
	parser = ArgumentParser(description='Client for RPi LEDs')
	parser.add_argument('-p', '--port', type=int, default=1337)
	parser.add_argument('-i', '--host-address', required=True)
	parser.add_argument('-s', '--song-path', required=True)
	parser.add_argument('-f', '--force-cache', action='store_true')
	args = parser.parse_args()

	port = args.port
	host = args.host_address
	song = abspath(args.song_path)
	song_name = basename(song)
	cache_name = Cache.get_cache_path(song)
	
	client = LEDClient(host, port)
	client.connect()

	limits = LimitsHandler()
	
	f = wave.open(song)
	levels = limits.generate_limits(f)
	
	Cache.write_cache(levels, cache_name)
	succ = Cache.transfer_cache(client, cache_name)

	d = wave.open(abspath(song))
	p = pa.PyAudio()

	#print str(d.getnchannels())
	#print str(d.getframerate())
	#print str(d.getsampwidth())

	stream = p.open(format=p.get_format_from_width(d.getsampwidth()),
		channels=d.getnchannels(),
		rate=d.getframerate(),
		output=True)

	sample_rate = d.getframerate()
	data = d.readframes(limits.chunk_size)
	it = 0

	client.send_command("go")

	while data != '':
		it += 1
		stream.write(data)
		data = d.readframes(limits.chunk_size)

	print "Finished stream thing"

	stream.stop_stream()
	stream.close()
	p.terminate()

	client.close()
	
if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print "Closing due to KeyboardInterrupt.."