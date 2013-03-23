import sys
from traceparser import *
import copy
import unittest
import traceparser

class BackTrace:
	"""Enables us to trace back in time"""
	def __init__(self, origTrace, cacheSize = 10000):
		self.trace = origTrace
		self.cacheSize = cacheSize
		self.cacheStartTime = 9999999999
		self.time = 1
		self.seek(0)
	def seek(self, time):
		cacheStartTime = max(0, time - self.cacheSize)
		self.cacheStartTime = cacheStartTime
		self.trace.seek(cacheStartTime)
		curTime = cacheStartTime
		iter = self.trace.iterate()
		self.cache = defaultdict(None)
		cache = self.cache

		while curTime <= time:
			curTime, eip = iter.next()
			regs = copy.deepcopy(self.trace.regs)
			cache[curTime] = (curTime, eip, regs)
		self.time = time
	def iterate(self):
		#print >>sys.stderr, "In BackTrace time:",self.time
		while self.time>=0:
			t = self.time
			cache = self.cache

			if self.cache.has_key(t) == False:
				self.time -= 1
				continue

			self.regs = cache[t][2]
			yield cache[t][0], cache[t][1]
			self.time -= 1
			if self.time<=self.cacheStartTime:
				self.seek(self.time)

		if self.time<0: self.time =0

class TestBackTrace(unittest.TestCase):
	def setUp(self):
		self.t = Trace("ex3\\trace.txt")
		self.memorySpace = FossileStream("ex3/dump")
		for temp in self.t.iterate(indexing=True):
			pass
		self.t.seek(0)
	def test1(self):

		forward = []
		backward = []
		iter = self.t.iterate()
		for i in xrange(10):
			forward.append(iter.next())

		backTrace = BackTrace(self.t, cacheSize = 2)
		backTrace.seek(9)	

		iter = backTrace.iterate()
		for i in xrange(10):
			backward.append(iter.next())
		for i in xrange(10):
			self.assertEqual(forward[i], backward[9 - i])



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
		self.javascriptFile = open("data.js","w")
		self.javascriptFile.write("var events = [\n")
		self.taintDict = {}

	def mark(self, memStart, fileStart, size):
		"""This maps the memory location from [memStart, memStart + size) 
		to [fileStart, fileStart + size)"""
		for i in xrange(size):
			self.taintDict[memStart + i] = "byte_%d" % (fileStart + i)

	def generateEvent(self,origins, address, instruction):
		decOrigins = []
		for origin in origins:
			decOrigins.append(origin[5:]) #XXX: Hideous hack, use proper data structures
		decOrigins.sort()
		self.javascriptFile.write("[ [%s], %d, '%s' ],\n" % (", ".join(decOrigins), address, str(instruction).replace("'","\\'")))
	def analyze(self, t, in_str):
		taintDict = self.taintDict
		for entry in changeMatrixIterator(t.iterate(), in_str):
			curTime, eip, instr, changeMatrix = entry

			#Before: Read taintDict to see the taint values of the locations that affected
			#the current instruction (by iterating through round 1)
			round2 = {}
			for key,val in changeMatrix.items():
				sources = [taintDict[x] for x in val if taintDict.has_key(x)]
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
				self.generateEvent(origins, eip, instr)
				print origins,"read by %08X" % eip
			
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
		self.javascriptFile.write("[-1]];\n")
		self.javascriptFile.write("var data = [\n")
		self.javascriptFile.write(", ". join( [hex(ord(memorySpace[BLOCK_START+i])) for i in range(BLOCK_LEN) ]))
		self.javascriptFile.write(" ];\n")
		self.javascriptFile.close()

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
