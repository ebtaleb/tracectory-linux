import sys
sys.path.append(".")
sys.path.append("./src")
import os
import json
from threading import Lock

try:
	import simplejson as json
except ImportError:
	import json


class Cycle:
	""" Represents the execution of one instructions at a certain point of time.  """
	def __init__(self, cpu, cycleNum):
		self.time = cycleNum
		self.cpu = cpu
		self.record = cpu.db.instructions.find_one( {'time' :  cycleNum }, {'_id' : 0}) 
		if self.record is None: raise KeyError
		#time, eip, instr, changeMatrix
		self.regs = self.record['regs']
	def getTime(self): return self.time
	def getPC(self): return self.record['PC']
	def getDisasm(self): return self.record['disassembly']
	def getEffects(self): return self.record['changes']
	def jsonDump(self):
		return json.dumps(self.record, indent = 4)
	def getMemoryRW(self):
		""" Returns a tuple (reads, writes) that contains the list of memory addresses
		    read/written. """
		reads, writes = set(), set()
		for dst, sources in self.getEffects().items():
			if str(dst).isdigit():
				writes.add(int(dst))
			for src in sources:
				if str(src).isdigit():
					reads.add(src)
		return list(reads), list(writes)

class CycleFactory:
	def __init__(self, db, parentTrace):
		self.db = db
		self.time = 0
		self.maxTime = parentTrace.getMaxTime()
		self.parentTrace = parentTrace
	def seek(self, time):
		self.time = time
		#print "Seeking to %d" % time	
	def getAt(self, time):
		cycle = self.getCycle(time)
		if cycle is None: return None
		self.regs = cycle.regs
		return (cycle.getTime(), cycle.getPC(), cycle.getDisasm(), cycle.getEffects())
	def getCycle(self, time):
		try: return Cycle(self, time)
		except KeyError: return None
	def oldIterate(self, delta = 1):
		while self.time>=0 and self.time<=self.maxTime:
			result = self.getAt(self.time)
			if result is not None:
				yield result
			self.time += delta
	def iterateCycles(self, startCycle, maxCycles = -1, delta = 1):
		cycleCount = 0
		t = startCycle
		while t>=0 and t<=self.maxTime:
			if cycleCount == maxCycles: break
			cycle = self.getCycle(t)
			if cycle is not None: 
				yield cycle
			cycleCount += 1
			t += delta
		
	def dumpState(self):
		try:
			return self.getCycle(self.time).jsonDump()
		except KeyError:
			return "{}"

