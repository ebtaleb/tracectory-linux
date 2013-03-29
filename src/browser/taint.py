import sys
#from traceparser import *
import copy
import unittest
from md5 import md5
import struct

class Entry:
	def __init__(self, name, parents = [], disasm = None):
		self.name = name
		self.parents = parents
		self.disasm = disasm
		self.origins = None
	def __repr__(self):
		return self.name
	def backtrace(self, level = 0):
		print " "*(2*level) + self.disasm
		for parent in self.parents:
			if isinstance(parent, Entry):
				parent.backtrace(level+1)
	def listOrigins(self):
		if self.origins is not None: return self.origins
		result = set()
		for parent in self.parents:
			if isinstance(parent, Entry):
				result |= parent.listOrigins()
			else:
				result.add(parent)
		self.origins = result
		return result

class ForwardTaintAnalyzer:
	"""This is used to trace the usage of certain values (such as file contents)
	   during the traced time"""
	def __init__(self):
		self.taintDict = {}

	def mark(self, memStart, fileStart, size):
		"""This maps the memory location from [memStart, memStart + size) 
		to [fileStart, fileStart + size)"""
		for i in xrange(size):
			self.taintDict[str(memStart + i)] = (fileStart + i)

	def generateEvent(self,origins, curTime, eip):
		decOrigins = []
		for origin in origins:
			decOrigins.append(origin) 
		decOrigins.sort()
		self.results.append( (decOrigins, curTime, eip))
	def analyze(self, t, MAX_STEPS = 10000):
		taintDict = self.taintDict
		self.results = []
		t.seek(0)
		count = 0
		for entry in t.iterate():
			if count > MAX_STEPS: break
			curTime, eip, instr, changeMatrix = entry
			count += 1
			#Before: Read taintDict to see the taint values of the locations that affected
			#the current instruction (by iterating through round 1)
			round2 = {}
			for key,val in changeMatrix.items():
				sources = [taintDict[str(x)] for x in val if taintDict.has_key(x) or taintDict.has_key(str(x))]
				if len(sources):
					round2[key] = Entry("Instruction %08X" % eip, sources, str(instr)) 
				else:
					round2[key] = None #This marks that the value was overwritten (with a constant)
			roundSet = set(round2.values())
			if None in roundSet: roundSet.remove(None)

			if len(roundSet)>0:
				origins = set()
				for curSource in roundSet:
					origins |= curSource.listOrigins()
				self.generateEvent(origins, curTime, eip)
				#print origins,"read by %08X" % eip
			
			# After: Commit results of this instruction to taintDict
			# Note that we cannot do this in the previous loop as the contents of
			# taintDict could change mid-instruction. The changes are supposed 
			# to take effect only _after_ the execution of the instruction.
			for key,val in round2.items():
				if val is None:
					if taintDict.has_key(key):
						del taintDict[key]
				else:
					taintDict[key] = val
		return self.results
	def toGraph(self, data):
		#Foramt of packed data: [ set(bytes), PC values ]
		packedData = []

		for entry in data:
			curBytes = set(entry[0])
			if len(packedData)>0 and curBytes == packedData[-1][0]:
				packedData[-1][1].append(entry[2])
			else:
				packedData.append( [curBytes, [entry[2]]])
		result = []
		for entry in packedData:
			locations =list(sorted(list(entry[0])))
			instrLocs = list(sorted(entry[1]))
			color = md5("".join([hex(x) for x in instrLocs])).digest()
			color = struct.unpack("<L", color[:3]+ "\x00")
			result.append( (locations, "#%06X" % color))
			
		return result
		

	
class BackLink:
	def __init__(self, time, eip, instr):
		self.time = time
		self.eip = eip
		self.instr = instr
		self.parents = []
	def link(self, newNode):
		self.parents.append(newNode)
	def __str__(self):
		if self.time is None:
			return "Final value"
		return "%d/%08X %s" % (self.time, self.eip, self.instr)
	def dump(self):
		nodes = set()
		current = [self]
		edges = []
		while len(current):
			next = set()

			for curNode in current:
				nodes.add(str(curNode))
				for p in curNode.parents:
					edges.append((str(curNode), str(p)))
					next.add(p)
			current = next
		return nodes, edges


class BackwardDataFlow:
	def __init__(self, trace):
		self.trace = trace
	def follow(self, address, time, MAX_TRACE = 1000):
		#TODO: Loop from time to time-MAX_TRACE
		backtrace = self.trace
		first = BackLink(None, None, None)
		address = str(address)
		taintDict = { address: first }
		backtrace.seek(time)
		#XXX: Migrate to new engine when it gets better
		i = 0
		for entry in backtrace.iterate(delta = -1):

			if i>MAX_TRACE: break
			i += 1

			curTime, eip, instr, changeMatrix = entry
			round2 = {}
			for key,sourceList in changeMatrix.items():
				#key is overwritten by values from data coming from <val>
				if not taintDict.has_key(key): continue
				oldVal = taintDict[key]
				del taintDict[key]
				#We taint all sources by the key
				for curSource in sourceList:
					round2[curSource] = BackLink(curTime, eip, instr)
					oldVal.link(round2[curSource])
			for k,v in round2.items():
				taintDict[str(k)] = v
			#print taintDict
		return first


def run2():
	t = Trace("ex3/trace.txt")
	memorySpace = FossileStream("ex3/dump")

	df = BackwardDataFlow(t, memorySpace)
	root = df.follow(0x404053, 135)
	print root.dump()
		

if __name__ == "__main__":
	run2()
	#unittest.main()
