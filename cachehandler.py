import gzip
import wave
import posixpath as nx
import ntpath as nt
from base64 import b64encode, b64decode
from os.path import abspath, basename, splitext, isfile

class Cache(object):
	@staticmethod
	def write_cache(limits, path, song, chunk_size=2048):
		if limits is None:
			print "Warning: 'limits' is null"
		with open(song, 'rb') as fi:
			wf = wave.open(fi)
			sample_rate = str(wf.getframerate())
			channels = str(wf.getnchannels())
			chunk = wf.readframes(chunk_size)
		with gzip.open(path, 'wb') as f:
			f.write(sample_rate + ":")      # index 0
			f.write(channels + ":")         # index 1
			f.write(b64encode(chunk) + ":") # index 2
			values = []
			for i in range(0, len(limits)):
				values.append(",".join([str(limits[i][j]) for j in range(0, len(limits[i]))]))
			f.write(';'.join(values))       # index 3

	@staticmethod
	def read_cache(path):
		limits = []
		print "Reading cache:", basename(path)
		with gzip.open(path, 'rb') as f:
			data = f.read().split(':')
			sample_rate = int(data[0])
			channels = int(data[1])
			chunk = b64decode(data[2])
			values = data[3].split(';')
			for val in values:
				line = val.split(',')
				limits.append([float(line[i]) for i in range(0, len(line))])
		print "Cache reading completed: {0} entries read".format(str(len(limits)))
		return (sample_rate, channels, chunk, limits)

	@staticmethod
	def transfer_cache(ledsocket, filename, force_transfer=False):
		ledsocket.send(filename)
		ledsocket.wait_command("forcecache", force_transfer)
		if force_transfer == False:
			hascache = ledsocket.send_command("hascache")
			if hascache:
				print "Cache already exists.."
				return False
			else:
				print "Cache is needed.."
		else:
			print "Info: FORCE_CACHE enabled"
		print "Transfering cache:", filename
		with open(filename, 'rb') as f:
			data = f.read(ledsocket.buffer_size)
			ledsocket.send(data)
			l = len(data)
			while len(data) != 0:
				data = f.read(ledsocket.buffer_size)
				if len(data) == 0:
					#print "__EOF__"
					ledsocket.send("__EOF__")
					break
				ledsocket.send(data)
				l += len(data)
			print "Sent {0} bytes".format(str(l))
		print "Cache transfered successfully"
		return True

	@staticmethod
	def recieve_cache(ledsocket):
		filename = ledsocket.recv()
		path = ""
		if '\\' not in nt.basename(path):
			path = abspath(nt.basename(filename))
		else:
			path = abspath(basename(filename))
		force = ledsocket.send_command("forcecache")
		if force == False:
			exists = isfile(path)
			ledsocket.wait_command("hascache", exists)
			if exists == True:
				print "Cache already exists.."
				return path
			else:
				print "Cache does not exist, recieving cache.."
		else:
			print "Info: FORCE_CACHE enabled"
		print "Fetching cache.."
		with open(path, 'wb') as f:
			data = ledsocket.recv()
			f.write(data)
			l = len(data)
			while "__EOF__" not in data:
				data = ledsocket.recv()
				if "__EOF__" in data:
					d = data[:len(data) - len("__EOF__")]
					l += len(d)
					f.write(d)
					#print str(len(d))
				else:
					f.write(data)
					l += len(data)
					#print str(len(data))
			#print "__EOF__"
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