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
import decoder
import fft

HOST = "192.168.1.218"
PORT = 1337
SOCK = None
SOCK_ONLINE = True
SOCK_THREAD = None
_SOCKET_CHUNK_SIZE = 512
_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

SPI = spidev.SpiDev()
SPI_INIT = False
BITS_PER_PIXEL = 3
NUM_LEDS = 32
GAMMA = bytearray(256) # gamma correction table

CHUNK_SIZE = 2048

# Helper functions

def gen_gamma_table():
	gamma = bytearray(256)
	for i in range(256):
		# https://github.com/scottjgibson/PixelPi/blob/master/pixelpi.py#L604
		gamma[i] = int(pow(float(i) / 255.0, 2.5) * 255.0)
	global GAMMA
	GAMMA = gamma
	print "Generated gamma table"

def gen_mono_arr(numleds, intcolor):
	return [GAMMA[intcolor] for _ in range(0, numleds * BITS_PER_PIXEL)]

# SPI functions

def open_spi(x, d):
	global SPI
	global SPI_INIT
	SPI.open(x, d)
	SPI_INIT = True
	print "SPI Interface ready for abuse -> /dev/spidev" + str(x) + "." + str(d)

def write_spi(byte_arr):
	SPI.writebytes(byte_arr)

def close_spi():
	if SPI_INIT != False:
		print "\nClosing interface.."
		off = gen_mono_arr(32, 0)
		write_spi(off)
		SPI.close()

# Main or something

def shutdown():
	print "shutdown pls work"
	_SOCKET.close()
	close_spi()
	sys.exit(1)

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
	cache_filename = os.path.abspath(os.path.splitext(filename)[0] + ".cache")
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

def recieve_cache(close_socket=True):
	#_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print "Listening.."
	_SOCKET.connect((HOST, PORT))
	print "Connected to: ", (HOST, PORT)
	data = _SOCKET.recv(_SOCKET_CHUNK_SIZE)
	buff = ""
	while data != '':
		buff += data
		data = _SOCKET.recv(_SOCKET_CHUNK_SIZE)
		#print str(len(data))
		#if "done" in data:
		#	break
	print "Length of recv: ", len(buff)
	#if close_socket:
	#	print "Closing connection"
	_SOCKET.close()
	#_SOCKET.send("done")
	return buff # return base64 encoded gzip data

def save_cache_to_file(raw_base64_cache):
	print raw_base64_cache[:10]
	name = raw_base64_cache.split(':')[0]
	data = raw_base64_cache.split(':')[1]
	print name
	print data[:30]
	#print name
	#print data[:10] + ".." + data[10:]
	cache_filename = name + ".cache"
	cache_path = os.path.abspath(cache_filename)
	decode_cache = base64.b64decode(data)
	with open(cache_path, 'wb') as f:
		f.write(decode_cache)
	print "Saved cache to: ", cache_path
	return cache_filename

def prepare_socket():
	_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print "Connecting on port: ", PORT
	_SOCKET.connect((HOST, PORT))
	print "Connected to client: ", (HOST, PORT)
	_SOCKET_INIT = True
	return _SOCKET

def main():
	cache = recieve_cache()
	filename = save_cache_to_file(cache)
	limits = read_cache(filename)
	
	#sys.exit(1)
	print "lol"

	open_spi(0,0)
	gen_gamma_table()

	SPI.max_speed_hz = 44100 #1300000

	print "lol"

	LEDS = []
	for i in range(0, 32):
		l = []
		for _ in range(0, i):
			l.extend([GAMMA[255],GAMMA[0],GAMMA[0]])
		for _ in range(0, 32 - i):
			l.extend([0x00, 0x00, 0x00])
		#print l
		LEDS.append(l)

	#sys.exit()

	socke = prepare_socket()

	print "Listenting for things"
	r = socke.recv(_SOCKET_CHUNK_SIZE)
	it = 1
	i = 10
	prev = 0

	while r != '':
		i += 1
		it += 1
		if it >= 31:
			it = 0
		l = (int((limits[i][2] - 6) * 3)) + 1
		#print "l: ", str(l)
		#print "L: ", l
		#arr = [GAMMA[255] for _ in range(0, l)]
		#for _ in range(0, (32 - l)):
		#	arr.append(0)
		write_spi(LEDS[(l + prev) / 2]) # gen_mono_arr(32, ))
		prev = l

		r = socke.recv(_SOCKET_CHUNK_SIZE)
		#print r

	print "it finished yay"
	
	#parser = argparse.ArgumentParser()
	#filegroup = parser.add_mutually_exclusive_group()
	#filegroup.add_argument('-f', '--file', help="file to play")
	#args = parser.parse_args()
	#SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#awd = SOCK.connect((HOST, PORT))
	#print "Connected to: "
	#print awd
	#print "lol"
	#SOCK_THREAD = threading.Thread(target=handle_master)
	#SOCK_THREAD.start()

	#if args.file == None:
	#	print "No file to play, closing app"
	#	print "actually no lol"
	#else:
	#	print "Playing: " + args.file + "\n"

	#file_path = os.path.abspath(args.file)
	#music_file = decoder.open(file_path)
	#sample_rate = music_file.getframerate()
	#num_channels = music_file.getnchannels()
	#seconds = music_file.getnframes() / sample_rate

	#print str(sample_rate)
	#print str(num_channels)
	#print str(music_file.getnframes())
	#print str(music_file.getnframes() / sample_rate) + "s"
	#print str(int(math.floor(seconds / 60))) + "m "+ str(seconds % 60) + "s"

	#row = 0
	#print CHUNK_SIZE
	#data = None
	# for i in range(0, 40):
	#data = music_file.readframes(CHUNK_SIZE)

	#print "sum or something", np.sum(data)

	#print "data length: ", len(data)
	#freq_limits = fft.calculate_levels(data, CHUNK_SIZE, sample_rate, [ [20, 1000], [1000, 5000], [5000, 7000], [7000, 10000], [10000, 150000] ], 5, 2)

	#print freq_limits

	#arr = gen_mono_arr(32, 255)
	#write_spi(arr)
	#print str(len(sys.argv))

	#print "yay it worked"
	socke.close()
	_SOCKET.close()
	close_spi()

if __name__ == '__main__':
	print "So far so good.."
	try:
		main()
	except KeyboardInterrupt:
		print "Exit(1): KeyboardInterrupt"
		_SOCKET.close()
		close_spi()