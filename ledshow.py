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

HOST = "192.168.1.218"
PORT = 1337
SOCK = None
SOCK_ONLINE = True
SOCK_THREAD = None
SOCKET_CHUNK_SIZE = 512
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
	return gamma

def gen_mono_arr(numleds, intcolor):
	return [GAMMA[intcolor] for _ in range(0, numleds * BITS_PER_PIXEL)]

# SPI functions

def open_spi(x, d):
	global SPI
	global SPI_INIT
	SPI.open(x, d)
	SPI_INIT = True
	print "SPI Interface ready -> /dev/spidev" + str(x) + "." + str(d)

	SPI.max_speed_hz = 1000000

	print "SPI Mode: " + str(SPI.mode)
	print "SPI Bits Per Word: " + str(SPI.bits_per_word)
	print "SPI Max Speed: " + str(SPI.max_speed_hz) + " Hz (" + str(SPI.max_speed_hz/ 1000) + " KHz)"

def write_spi(byte_arr):
	SPI.writebytes(byte_arr)

def close_spi():
	if SPI_INIT != False:
		print "Closing interface.."
		off = gen_mono_arr(32, 0)
		write_spi(off)
		SPI.close()

# Main or something

def shutdown():
	print "Shutting down.."
	SOCKET.close()
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

def prepare_socket():
	SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	print "Connecting on port: ", PORT
	SOCKET.connect((HOST, PORT))
	print "Connected to client: ", (HOST, PORT)
	SOCKET_INIT = True
	return SOCKET

def main():
	parser = argparse.ArgumentParser(description='Client for RPi LEDs')
	parser.add_argument('-p', '--port', type=int, default=1337)
	parser.add_argument('-i', '--host-address', required=True)
	parser.add_argument('-s', '--song-path', required=True)
	args = parser.parse_args()

	port = args.port
	host = args.host_address
	song = os.path.abspath(args.song_path)
	song_name = os.path.basename(song)

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

	open_spi(0,0)
	GAMMA = gen_gamma_table()

	LEDS = []
	for i in range(0, 32):
		l = []
		for _ in range(0, i):
			l.extend([GAMMA[255],GAMMA[255],GAMMA[255]])
		for _ in range(0, 32 - i):
			l.extend([0x00, 0x00, 0x00])
		LEDS.append(l)

	print "Listenting for things"
	socke = prepare_socket()
	it = 1
	i = 0
	prev = 0

	r = socke.recv(SOCKET_CHUNK_SIZE)

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
	socke.close()
	SOCKET.close()
	close_spi()

if __name__ == '__main__':
	print "So far so good.."
	try:
		main()
	except KeyboardInterrupt:
		print "losing down.."
		SOCKET.close()
		close_spi()