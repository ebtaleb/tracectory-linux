from datastore.DataFlow import *
from taint import *

class MemoryHistory:
	def __init__(self, target):
		self.oldDB = target.getDB("old")
		self.newDB = target.getDB("new")
		self.trace = DataFlow(self.oldDB)
		self.newDF = DataFlow(self.newDB)
		#self.trace = trace
		#self.mem = mem

# def readAt(addrOfByte, timeSlot)
#      - use binary search to find largest i suchthat writtenAt[addr][i]<timeSlot
#      - seek to writtenAt[addr][i], if mov -> can produce result
#      - alternatively try seeking the next read 
#       we could also return the time when this was last written to
#     O(log n)

	def previousWrite(self, addr, time):
		#Binary search, logarithmic time
		addr = str(addr)
		lower = 0
		try:
			upper = int(self.oldDB.Get("write_%s_ctr" % addr)) - 1
		except KeyError:
			return None
		while lower+1<upper:
			middle = (lower+upper)/2
			value = int(self.oldDB.Get("write_%s_%d" % (addr, middle)))
			if value>time:
				upper = middle - 1
			else:
				lower = middle
		if upper == -1:
			return None
		upperVal = int(self.oldDB.Get("write_%s_%d" % (addr,upper)))
		if upperVal<=time: return upperVal
		lowerVal = int(self.oldDB.Get("write_%s_%d" % (addr,lower)))
		if lowerVal<=time: return lowerVal

		return None
	def get(self, address, time):
		result = self.getWithTime(address,time)
		return result[0]
	def getWithTime(self, address, time):
		writtenAt = self.previousWrite(address, time)
		if writtenAt is None:
			return None
		self.newDF.seek(writtenAt)
		for entry in self.newDF.iterate():
			curTime, eip, instr, changeMatrix = entry
			for dest, sources in changeMatrix.items():
				if str(dest) == str(address):
					#XXX: Add proper data structure
					source = sources[0]
				
					if isinstance(source, str) or isinstance(source, unicode):
						source = str(source).strip()
						regName = source[:source.find("_")]
						index = int(source[source.find("_")+1:])
						fullVal = self.newDF.regs[regName.upper()]
						return ((fullVal>>index) & 0xff), curTime
					else:
						return source, curTime

			break
		return None






#A = TaintAnalyzer()
#BLOCK_START = 0x40305c
#BLOCK_LEN = 14
#BLOCK_START = 0x403064
#BLOCK_LEN = 51
#TA.mark(BLOCK_START, 0, BLOCK_LEN)


