import gzip
import posixpath as nx
import ntpath as nt
from os.path import abspath, basename, splitext, isfile

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
			while len(data) != 0: #data != '':
				data = f.read(ledsocket.buffer_size)
				if len(data) == 0:
					print "__EOF__"
					ledsocket.send("__EOF__")
					break
				ledsocket.send(data)
				l += len(data)
				#if len(data) > 0:
				#	print len(data)
			print "Sent {0} bytes".format(str(l))
		#ledsocket.recv()
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
					print str(len(d))
				else:
					f.write(data)
					l += len(data)
					print str(len(data))
			print "__EOF__"
			print "Recieved {0} bytes".format(str(l))
		#ledsocket.send("usuk")
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
