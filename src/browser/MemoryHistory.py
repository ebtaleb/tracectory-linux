from datastore.DataFlow import *
from taint import *
from collections import defaultdict


class MemoryAccess:
	def __init__(self, history, address, time, readOrWrite):
		"""Not meant to be initialized from outside MemoryHistory"""
		self.history = history
		self.address = address
		self.time = time
		self.readOrWrite = readOrWrite
	def getType(self): return self.readOrWrite
	def getAddress(self): return self.address
	def getTime(self): return self.time
	def getValue(self):
		if self.readOrWrite == "R":
			return self.history.getByteReadAt(self.address, self.time)
		elif self.readOrWrite == "W":
			return self.history.getByteWrittenAt(self.address, self.time)
		else:
			raise ValueError, "Inconsistent state / neither read nor write"
	def previousWrite(self):
		t = self.history.previousWrite(self.address, self.time)
		if t is None: return None
		return MemoryAccess(self.history, self.address, t, "W")
	def nextRead(self):
		t = self.history.nextRead(self.address, self.time)
		if t is None: return None
		return MemoryAccess(self.history, self.address, t, "R")
	def isRead(self):  return  self.readOrWrite == "R"
	def isWrite(self): return self.readOrWrite == "W"

	def __repr__(self):
		return "<MemoryAccess: %s%08X (t = %d)>" % (self.getType(), int(self.getAddress()), self.getTime())


class MemoryHistory:
	def __init__(self, target):
		self.oldDB = target.getDB("old")
		self.newDB = target.getDB("new")
		self.trace = DataFlow(self.oldDB, target)
		self.newDF = DataFlow(self.newDB, target)

# def readAt(addrOfByte, timeSlot)
#      - use binary search to find largest i suchthat writtenAt[addr][i]<timeSlot
#      - seek to writtenAt[addr][i], if mov -> can produce result
#      - alternatively try seeking the next read 
#       we could also return the time when this was last written to
#     O(log n)

	############# List functions ##########
	def __binSearchList(self, listName, value):
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
	def __getListValuesInRange(self, listName, minVal, maxVal):
		lower = self.__binSearchList(listName, minVal)
		if lower is None: return []
		lower += 1
		count = self.__listCount(listName)

		if lower >= count: return []
		upper = self.__binSearchList(listName, maxVal)
		if upper is None:
			#Upper not found but lower found -> upper = max
			upper = count - 1
		
		result = []
		for i in xrange(lower,upper+1):
			result.append(self.__getListInt(listName, i))
		return result

	############# /List functions #########
	def previousWrite(self, addr, time):
		key = "write_%d" % addr
		index = self.__binSearchList(key, time)
		if index is None or index == -1: return None
		return self.__getListInt(key, index)
	def nextRead(self, addr,time):
		key = "read_%d" % addr
		index = self.__binSearchList(key, time)
		if index is None: return None
		if (index+1) >= self.__listCount(key):
			return None
		return self.__getListInt(key, index + 1)
	def nextWrite(self, addr,time):
		key = "write_%d" % addr
		index = self.__binSearchList(key, time)
		if index is None: return None
		if (index+1) >= self.__listCount(key):
			return None
		return self.__getListInt(key, index + 1)



	def get(self, address, time):
		result = self.getWithTime(address,time)
		if result is None: return None
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
		#Confirm that there is no intervening write that could have changed the value 
		#in between
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
				#We can deduce the value if there is only one data source
				if len(sources) > 1: return None
				source = sources[0]
			
				if isinstance(source, str) or isinstance(source, unicode):
					#XXX: Add proper data structure
					source = str(source).strip()
					regName = source[:source.find("_")]
					index = int(source[source.find("_")+1:])
					if regName == "const":
						return index
					fullVal = self.newDF.regs[regName.upper()]
					return ((fullVal>>index) & 0xff)
				else:
					#TODO: Likely another memory address, should
					#we continue tracing?
					return None

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
			
				
	def iterMemoryEvents(self, byteArray, startTime, endTime, groupByTime = False):
		""" Iterates all memory reads/writes between startTime and endTime to/from
		    memory locations in byteArray"""
		eventsByTime = defaultdict(list)
		for byteIdx in xrange(0, len(byteArray)):
			curAddr = byteArray[byteIdx]
			l = "read_%d" % curAddr
			for curTime in  self.__getListValuesInRange(l, startTime, endTime):
				eventsByTime[curTime].append( 
					MemoryAccess(self, curAddr, curTime, "R")
				)

			l = "write_%d" % curAddr
			for curTime in  self.__getListValuesInRange(l, startTime, endTime):
				eventsByTime[curTime].append( 
					MemoryAccess(self, curAddr, curTime, "W")
				)
		if groupByTime:
			keys = eventsByTime.keys()
			result = []
			for curTime in sorted(keys):
				yield (curTime, eventsByTime[curTime] )
		else:
			for curTime in sorted(eventsByTime.keys()):
				for event in eventsByTime[curTime]: yield event

	def memoryGraph(self, eventList, compress = True, minAddr = 0):
		"""If compress is True, removes all references to memory locations that 
		   were not present in the observed time slice"""
		if not compress:
			result = []
			for time, events in eventList:
				tuples = [ (x.getAddress() - minAddr, x.getType()) for x in events]
				result.append( ( time, tuples) )
 			return result, None

		seenAddrs = set()
		for curRow in eventList:
			for curAccess in curRow[1]:
				seenAddrs.add(curAccess.getAddress())
		
		#Create a dict that maps old addresses to compressed values
		sortedAddrs = list(sorted(list(seenAddrs)))
		mapDict = dict( (sortedAddrs[i], i) for i in xrange(len(sortedAddrs)))
		compressedList = []

		#Apply the dict transform to each event
		for curRow in eventList:
			newCols = [ (mapDict[x.getAddress()], x.getType()) for x in curRow[1]]
			compressedList.append( (curRow[0], newCols) )
		return compressedList, sortedAddrs

	

			
