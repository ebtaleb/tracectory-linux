from Cycle import *
from taint import *
from collections import defaultdict
import json

class MemoryAccess:
	"""MemoryAccess objects represent a memory access (read/write) at a certain
	   point in time. Instance methods can ge used to retrieve the address and 
	   time, try to resolve the value written/read or navigate to next/previous
	   writes to the same location"""
	def __init__(self, history, address, time, readOrWrite):
		"""Not meant to be initialized from outside MemoryHistory"""
		self.history = history
		self.address = address
		self.time = time
		self.readOrWrite = readOrWrite
	def getType(self): return self.readOrWrite
	def getAddress(self): return self.address
	def getTime(self): return self.time
	def isRead(self):  return  self.readOrWrite == "R"
	def isWrite(self): return self.readOrWrite == "W"
	def getValue(self):
		if self.isRead():
			return self.history.getByteReadAt(self.address, self.time)
		elif self.isWrite():
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

	def __repr__(self):
		return "<MemoryAccess: %s%08X (t = %d)>" % (self.getType(), int(self.getAddress()), self.getTime())

class MemoryLocation:
	"""Represents a memory location that was written/read during the trace."""
	def __init__(self, history, loc):
		self.history = history
		self.loc = loc
	def numReads(self):
		return self.history.db.reads.find( {'addr' : self.loc }).count()
	def numWrites(self):
		return self.history.db.writes.find( {'addr' : self.loc }).count()
	def getLastRead(self):

		reads = self.numReads()
		if reads == 0: return None

		l = list(self.history.db.reads.find({'addr' : self.loc }).sort( {'time' : -1}).limit(1))
		return l[0]
	def getLastWrite(self):

		reads = self.numWrites()
		if reads == 0: return None

		l = list(self.history.db.writes.find({'addr' : self.loc }).sort( {'time' : -1}).limit(1))
		return l[0]

	def __repr__(self):
		return "<MemoryLocation: %08X (writes: %d, reads: %d)>" % (int(self.loc), self.numWrites(), self.numReads())


class MemoryHistory:
	def __init__(self, target):
		self.db = target.getDB()
		self.newDF = CycleFactory(self.db, target)
		self.target = target
		self.memAddrs = None
 
	def previousWrite(self, addr, time):
		l = list(self.db.writes.find( {"addr" : addr , "time" : { "$lt" :  time  }} ).sort("time", direction = -1).limit(1))
		if len(l) == 0: return None
		return l[0]['time']

	def nextRead(self, addr,time):
		l = list(self.db.reads.find( {"addr" : addr , "time" : { "$gt" :  time  }} ).limit(1))
		if len(l) == 0: return None
		return l[0]['time']

	def nextWrite(self, addr,time):
		l = list(self.db.writes.find( {"addr" : addr , "time" : { "$gt" :  time  }} ).limit(1))
		if len(l) == 0: return None
		return l[0]['time']

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
		nextWrite = self.nextWrite(address,writtenAt+1) #XXX: Check off-by one
		if nextWrite is not None and nextWrite<readAt:
			return None

		if readAt is None: return None
		value = self.getByteReadAt(address, readAt)
		if value is not None:
			return value, -1
		
	def getByteWrittenAt(self, address, writtenAt):
		cycle = self.newDF.getCycle(writtenAt)
		if cycle is None: return None
		changeMatrix = cycle.getEffects()
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
					fullVal = cycle.regs[regName.upper()]
					return ((fullVal>>index) & 0xff)
				else:
					#TODO: Likely another memory address, should
					#we continue tracing?
					return None

		return None

	def getByteReadAt(self, address, readAt):
		iterator = self.newDF.iterateCycles(readAt)
		readCycle = iterator.next()
		nextCycle = iterator.next()  #We need reg values AFTER the read cycle
		for dest, sources in readCycle.getEffects().items():
			if len(sources) != 1: continue
			if str(sources[0]) != str(address):  continue
			#We've found out that the data was written to dest
			dest = str(dest).strip()
			if "_" not in dest: continue #Flags etc.

			regName = dest[:dest.find("_")]
			index = int(dest[dest.find("_")+1:])
			fullVal = nextCycle.regs[regName.upper()]
			val = (fullVal>>index)&0xff
			return val
		return -1
			
				
	def iterMemoryEvents(self, byteArray, startTime, endTime, groupByTime = False):
		""" Iterates all memory reads/writes between startTime and endTime to/from
		    memory locations in byteArray"""
		eventsByTime = defaultdict(list)
		for byteIdx in xrange(0, len(byteArray)):
			curAddr = byteArray[byteIdx]
			reads = self.db.reads.find( {'addr' : curAddr, 'time' : { '$gte' : startTime, '$lte' : endTime}})
			for curRead in reads:
				curTime = int(curRead['time'])
				eventsByTime[curTime].append( 
					MemoryAccess(self, curAddr, curTime, "R")
				)

			writes = self.db.writes.find( {'addr' : curAddr, 'time' : { '$gte' : startTime, '$lte' : endTime}})
			for curWrite in  writes:
				curTime = int(curWrite['time'])
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

	def checkForRange(self, table, startAddr, endAddr, startTime, endTime):
		sample = table.find_one({'addr' : {"$gte" : startAddr, "$lt" : endAddr }, 'time' : {"$gte" : startTime}}, 
			{'_id' : 0, "time" : 1})
		return (sample is not None and sample['time'] < endTime)


	def getOverview(self, timeResolution = 30, addrResolution=30, startBlock = 0, startTime = None, endTime = None, startAddr = 0, endAddr = None):	
		print "timeResolution = %d, addrResolution = %d" % (timeResolution, addrResolution)
		if self.memAddrs is not None:
			addresses = self.memAddrs
		else:
			readAddr = set(self.db.reads.distinct("addr"))
			writeAddr = set(self.db.writes.distinct("addr"))
			addresses = readAddr | writeAddr
			del readAddr
			del writeAddr
			self.memAddrs = addresses

		if endTime is None: endTime = self.target.getMaxTime()
		if startTime is None: startTime = 0
		if startAddr is None: startAddr = 0
		if endAddr is None: endAddr=999

		timeBucketSize = (endTime - startTime) / timeResolution
		addresses = list(sorted(list(addresses)))
		if startAddr in addresses:
			addresses = addresses[addresses.index(startAddr):]
		if endAddr in addresses:
			addresses = addresses[:addresses.index(endAddr):]
		addrBucketSize = len(addresses) / addrResolution

		curRow = None
		result = []
		maxVal = 0
		perOne = 8

		for row in xrange(perOne):
			y = row + startBlock	
			curAddr = addresses[y*addrBucketSize]
			if (y+1)*addrBucketSize >= len(addresses):
				curEnd = 2**65
			else:
				curEnd = addresses[(y+1) * addrBucketSize]
			if curRow is not None: result.append(curRow)
			curRow = []
			print "%08X-%08X" %(curAddr, curEnd)

			curEnd = curAddr + addrBucketSize
			for x in xrange(timeResolution):
				curTime = x*timeBucketSize + startTime
				wasRead = self.checkForRange(self.db.reads, curAddr, curEnd, curTime, curTime + timeBucketSize)
				wasWritten = self.checkForRange(self.db.writes, curAddr, curEnd, curTime, curTime + timeBucketSize)
				info = { "wasRead" : wasRead, "wasWritten" : wasWritten, "firstAddr" : curAddr, "firstTime" : curTime }
				curRow.append(info)

		if curRow is not None: result.append(curRow)	

		return json.dumps(result, indent=4)
	
