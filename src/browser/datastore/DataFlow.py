import sys
sys.path.append(".")
sys.path.append("./src")
import os
import json
from threading import Lock
import leveldb

try:
	import simplejson as json
except ImportError:
	import json

class DataFlow:
	def __init__(self, db):
		self.db = db
		self.time = 0
		self.maxTime = int(self.db.Get("maxTime"))
	def seek(self, time):
		self.time = time
		#print "Seeking to %d" % time	
	def getCur(self):
		try:
			#print "looking up '%s' " % str(self.time)
			recordStr = self.db.Get("instr_%d" % self.time)
		except KeyError:
			#print "Did not find '%s'" % str(self.time)
			return None
		record = json.loads(recordStr) 
		#time, eip, instr, changeMatrix
		self.regs = record['regs']
		return (self.time, record['PC'], record['disassembly'], record['changes'])
	def iterate(self, delta = 1):
		while self.time>=0 and self.time<=self.maxTime:
			result = self.getCur()
			if result is not None:
				yield result
			self.time += delta
	def dumpState(self):
		try:
			return self.db.Get("instr_%d" % self.time)
		except KeyError:
			return "{}"

