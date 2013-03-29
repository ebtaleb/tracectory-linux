from datastore.DataFlow import *
from taint import *
from collections import defaultdict

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

	############# List functions ##########
	def binSearch(self, listName, value):
		#Binary search, logarithmic time
		""" Returns largest x such that list[x]<=value """
		lower = 0
		try: upper = int(self.oldDB.Get("%s_ctr" % listName)) - 1
		except KeyError: return None
		#Searches for leq
		while lower+1<upper:
			middle = (lower+upper)/2
			curValue = int(self.oldDB.Get("%s_%d" % (listName, middle)))
			if curValue>value:
				upper = middle - 1
			else:
				lower = middle
		if upper == -1:
			return -1
		upperVal = int(self.oldDB.Get("%s_%d" % (listName, upper)))
		if upperVal <= value: return upper
		lowerVal = int(self.oldDB.Get("%s_%d" % (listName, lower)))
		if lowerVal <= value: return lower

		return -1

	def __listCount(self, listName): return int(self.oldDB.Get("%s_ctr" % listName))
	def __getListInt(self, listName, idx): return int(self.oldDB.Get("%s_%d" % (listName,idx)))

	############# /List functions #########
	def previousWrite(self, addr, time):
		key = "write_%d" % addr
		index = self.binSearch(key, time)
		if index is None or index == -1: return None
		return self.__getListInt(key, index)
	def nextRead(self, addr,time):
		key = "read_%d" % addr
		index = self.binSearch(key, time)
		if index is None: return None
		if (index+1) >= self.__listCount(key):
			return None
		return self.__getListInt(key, index + 1)
	def nextWrite(self, addr,time):
		key = "write_%d" % addr
		index = self.binSearch(key, time)
		if index is None: return None
		if (index+1) >= self.__listCount(key):
			return None
		return self.__getListInt(key, index + 1)



	def get(self, address, time):
		result = self.getWithTime(address,time)
		return result[0]
	def getWithTime(self, address, time):
		#Plan A: Look up previous write
		writtenAt = self.previousWrite(address, time)
		if writtenAt is not None:
			value = self.getByteWrittenAt(address, writtenAt)
			if value is not None:
				return value, writtenAt
		else:
			writtenAt = 0

		#Plan B: Next read after this unresolvable write
		readAt=self.nextRead(address, writtenAt)


		#XXX: Check that there is no intervening write
		nextWrite = self.nextWrite(address,writtenAt+1)
		if nextWrite is not None and nextWrite<readAt:
			return None

		if readAt is None: return None
		value = self.getByteReadAt(address, readAt)
		if value is not None:
			return value, -1
		
	def getByteWrittenAt(self, address, writtenAt):
		traceData = self.newDF.getAt(writtenAt)
		if traceData is None: return None
		curTime, eip, instr, changeMatrix = traceData
		for dest, sources in changeMatrix.items():
			if str(dest) == str(address):
				#XXX: Add proper data structure
				source = sources[0]
			
				if isinstance(source, str) or isinstance(source, unicode):
					source = str(source).strip()
					regName = source[:source.find("_")]
					index = int(source[source.find("_")+1:])
					if regName == "const":
						return index
					fullVal = self.newDF.regs[regName.upper()]
					return ((fullVal>>index) & 0xff)
				else:
					return source

		return None

	def getByteReadAt(self, address, readAt):
		self.newDF.seek(readAt)
		iterator = self.newDF.iterate()
		curTime, eip, instr, changeMatrix = iterator.next()

		iterator.next() #One step to make resgistry references refer
				#to values AFTER this instruction
		for dest, sources in changeMatrix.items():
			if len(sources) != 1: continue
			if str(sources[0]) != str(address):  continue
			#We've found out that the data was written to dest
			dest = str(dest).strip()
			if "_" not in dest: continue #Flags etc.

			regName = dest[:dest.find("_")]
			index = int(dest[dest.find("_")+1:])
			fullVal = self.newDF.regs[regName.upper()]
			val = (fullVal>>index)&0xff
			return val
		return -1
			
				
	def getValuesInRange(self, listName, minVal, maxVal):
		lower = self.binSearch(listName, minVal)
		if lower is None: return []
		lower += 1
		count = self.__listCount(listName)

		if lower >= count: return []
		upper = self.binSearch(listName, maxVal)
		if upper is None:
			#Upper not found but lower found -> upper = max
			upper = count - 1
		
		result = []
		for i in xrange(lower,upper+1):
			result.append(self.__getListInt(listName, i))
		return result
	def listMemoryEvents(self, byteArray, startTime, endTime):
		eventsByTime = defaultdict(list)
		for byteIdx in xrange(0, len(byteArray)):
			curAddr = byteArray[byteIdx]
			l = "read_%d" % curAddr
			for curTime in  self.getValuesInRange(l, startTime, endTime):
				eventsByTime[curTime].append( (byteIdx, "R"))

			l = "write_%d" % curAddr
			for curTime in  self.getValuesInRange(l, startTime, endTime):
				eventsByTime[curTime].append( (byteIdx, "W"))
		keys = eventsByTime.keys()
		result = []
		for curTime in sorted(keys):
			result.append( (curTime, eventsByTime[curTime] ))
		return result

	def getRW(self, changeMatrix):
		reads, writes = set()
		for dst, sources in changeMatrix.items():
			if str(dst).isdigit():
				writes.add(int(dst))
			for src in sources:
				if str(src).isdigit():
					reads.add(src)
		return reads, writes

	

			
