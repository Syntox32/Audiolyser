import wave
import os
import sys
import fft
import math
import spi
import gzip
import base64
import socket

import pyaudio as pa
import numpy as np

SONG = "downtheroad.wav"
HOST = "192.168.1.218"
PORT = 1337
CHUNK_SIZE = 2048

_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
_SOCKET_CHUNK_SIZE = 512
_SOCKET_INIT = True
_MAX_FREQ = 15000
_MIN_FREQ = 20
_GIOP_LEN = 5 # number of 'bars'
_N_CHANNELS = 2 # use 1 if mono
_FREQ_LIMITS = [ [20, 1000], [1000, 5000], [5000, 7000], [7000, 10000], [10000, 15000] ]

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
			#print line
			f.write(line)
	print "Length of limits: ", str(len(limits))
	return limits

def read_cache(filename):
	#cache_filename = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
	cache_filename = get_cache_path(filename)
	print "Reading cache: ", os.path.splitext(filename)[0] + ".cache"
	limits = []
	with gzip.open(cache_filename, 'rb') as f:
		line = f.readline()
		while line != '' or line == '\n':
			line = line.replace('\n', '').split(',')
			#print [float(line[i]) for i in range(0, len(line))]
			limits.append([float(line[i]) for i in range(0, len(line))])
			line = f.readline()
	print "Cache reading completed: " + str(len(limits)) + " entries read"
	return limits

def get_cache_filename(filename):
	return os.path.splitext(filename)[0] + ".cache"

def get_cache_path(filename):
	return os.path.abspath(os.path.splitext(filename)[0] + ".cache")

def check_if_cache_exists(filename):
	cache_path = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
	return os.path.isfile(cache_path)

def transfer_cache(filename, close_socket=True):
	#cache_filename = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
	cache_filename = get_cache_path(filename)
	print "Transfering cache: ", os.path.splitext(filename)[0] + ".cache"
	base_data = ""
	with open(cache_filename, 'rb') as f:
		base_data = base64.b64encode(f.read())
	base_data = os.path.splitext(filename)[0] + ":" + base_data
	print "Binding to client: ", (HOST, PORT)
	_SOCKET.bind((HOST, PORT))
	print "Listening on port: ", PORT
	_SOCKET.listen(1)
	(conn, addr) = _SOCKET.accept()
	#_CONN = conn
	#global _CONN
	print "Client connected from: ", addr
	print "Base64 Length: ", str(len(base_data))
	sent = conn.send(base_data[:_SOCKET_CHUNK_SIZE])
	sent_bytes = sent
	while sent != 0:
		sent = conn.send(base_data[sent_bytes:(sent_bytes + _SOCKET_CHUNK_SIZE)])
		sent_bytes += sent
	#conn.send('done')
	#print base_data[10:]
	print "Base64 Sent: ", str(sent_bytes)
	#feedback = conn.recv(_SOCKET_CHUNK_SIZE)
	#if "done" in feedback:
	#	print "cool"

	#if close_socket:
	#	print "Closing connection.."
	conn.close()
	#	print "Closing socket.."
	_SOCKET.close()
	print "Transfer completed, cya client.."
	# print base_data[:100]

def prepare_socket():
	_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print "Binding to client: ", (HOST, PORT)
	_SOCKET.bind((HOST, PORT))
	print "Listening on port: ", PORT
	_SOCKET.listen(1)
	(conn, addr) = _SOCKET.accept()
	print "Client connected from: ", addr
	_SOCKET_INIT = True
	return conn # return connection

def close_socket():
	if _SOCKET_INIT:
		print "Closing socket.."
		_SOCKET.close()

def main():
	print os.getcwd()
	print os.path.abspath(SONG)
	print "lol playing: ", SONG


	# if check_if_cache_exists == False:
	write_cache(SONG)
	transfer_cache(SONG)
	limits = read_cache(SONG)

	m = np.matrix(limits)
	print "max: ", m.max()
	print "mean:", m.mean()
	print "newmin: ", m.mean() - (m.max() - m.mean())
 
	#sys.exit(1)

	d = wave.open(os.path.abspath(SONG))
	p = pa.PyAudio()

	#print "Listening for another connectionl lol fix this pls"
	#_SOCKET.listen(1)
	#(conn, addr) = _SOCKET.accept()
	#print "Connection accpeted"

	conn = prepare_socket()

	print str(d.getnchannels())
	print str(d.getframerate())
	print str(d.getsampwidth())

	stream = p.open(format=p.get_format_from_width(d.getsampwidth()),
		channels=d.getnchannels(),
		rate=d.getframerate(),
		output=True)

	sample_rate = d.getframerate()
	data = d.readframes(CHUNK_SIZE)
	it = 0

	while data != '':
		conn.send("wc:" + str(it))
		#print "wc:" + str(it)
		it += 1
		#print limits[it - 1]
		stream.write(data)
		data = d.readframes(CHUNK_SIZE)
		#freq_limits = fft.calculate_levels(data, CHUNK_SIZE, sample_rate, _FREQ_LIMITS, _GIOP_LEN, _N_CHANNELS)
		#freq_limits = [int(math.floor(freq_limits[i])) for i in range(0, len(freq_limits))]
		# print (freq_limits)

	conn.send('')
	print "Finished stream thing"

	conn.close()
	close_socket()

	stream.stop_stream()
	stream.close()

	p.terminate()

	print "done lol"

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print "Exit(1): KeyboardInterrupt"
		close_socket()