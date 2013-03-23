from collections import defaultdict
import struct

class FossileStream:
	def __init__(self, fileName):
		fp = open(fileName, "rb")
		self.pages = {}
		self.quickSeek = {}
		while True:
			magic = fp.read(1)
			if len(magic) == 0:
				break
			if magic == "P":
				addr = struct.unpack("<L", fp.read(4))[0]
				reserved = struct.unpack("<L", fp.read(4))[0]
				data = fp.read(0x1000)
				self.pages[addr] = data
				#print "Read page ",hex(addr)
		self.offset = 0
		#print "Exiting loop"
	def seek(self, pos, mode = 0):
		#print "seek(%d,%d)" % (pos, mode)
		if mode == 2:
			self.offset = 0x80000000 - pos
		else:
			self.offset = pos
	def __len__(self):
		return 0x80000000
	def tell(self):
		return self.offset
	def __call__(self, start, end):
		self.seek(start)
		return self.read(end - start)
	def __getitem__(self, pos):
		return self.__call__(pos, pos+1)
	def read(self, size):
		page = self.offset&(~0xfff)
		offset = self.offset&0xfff
		self.offset += size
		return self.pages[page][offset:offset+size]
	def readbs(self, size=1):
		return self.read(size)

class Trace:
	SEEK_GRANULARITY = 1000
	def __init__(self, filename):
		self.fp = open(filename)
		self.regs = defaultdict(int)
		self.time = 0
		self.quickSeek = {}
	def seek(self, time):
		#print "Trace.seek(%d)" % time
		if time == 0:
			self.fp.seek(0)
			self.time = 0
			return
		howManySince = time % Trace.SEEK_GRANULARITY
		roundDown = (time/Trace.SEEK_GRANULARITY) * Trace.SEEK_GRANULARITY
		self.fp.seek(self.quickSeek[roundDown])
		i = 0
		self.time = roundDown 
		if howManySince>0:
			for curTime, eip in self.iterate():
				# XXX: time - 1 may never be reached
				if curTime == time - 1: break
		self.time += 1

	def iterate(self, maxSteps=0xffffffffff, indexing = False):
		endTime = self.time + maxSteps
		while self.time<endTime:
			if indexing and self.time%Trace.SEEK_GRANULARITY == 0:
				self.quickSeek[self.time] = self.fp.tell()
			line = self.fp.readline()
			eipData = line[6:line.find(" ",6)]
			if eipData.startswith("-"): break
			try:
				eip = int(eipData, 16)
			except ValueError:
				#print "Warning: Couldn't parse %s\n" % eipData
				yield self.time, None
				self.time += 1
				continue
			#yield eip
			regData = line[line.find("EAX="):].split(",")
			for val in regData:
				reg, value = val.split("=")
				self.regs[reg.strip()] = int(value,16)
			yield self.time, eip #Option: all registers seems to show the previous values?
			self.time += 1

