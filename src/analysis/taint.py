# This file contains code that can be used to trace dataflow (origin of value i.e. backward 
# data flow, or use of certain data i.e. forward data flow)
import sys
#from traceparser import *
import copy
import unittest
from md5 import md5
import struct

class Entry:
	def __init__(self, cycle, parents = []):
		self.cycle = cycle
		self.parents = parents
		self.__origins = None #cache for memoization
	def __repr__(self):
		return self.name
	def backtrace(self, level = 0):
		print " "*(2*level) + self.cycle.getDisasm()
		for parent in self.parents:
			if isinstance(parent, Entry):
				parent.backtrace(level+1)
	def listOrigins(self):
		if self.__origins is not None: return self.__origins
		result = set()
		for parent in self.parents:
			if isinstance(parent, Entry):
				result |= parent.listOrigins()
			else:
				result.add(parent)
		self.__origins = result
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
		decOrigins = list(origins)
		decOrigins.sort()
		self.results.append( (decOrigins, curTime, eip))
	def analyze(self, t, startTime, MAX_STEPS = 10000):
		taintDict = self.taintDict
		self.results = []
		for cycle in t.iterateCycles(startTime, maxCycles = MAX_STEPS):
			#Before: Read taintDict to see the taint values of the locations that affected
			#the current instruction (by iterating through round 1)
			round2 = {}
			for key,val in cycle.getEffects().items():
				sources = [taintDict[str(x)] for x in val if taintDict.has_key(x) or taintDict.has_key(str(x))]
				if len(sources):
					round2[key] = Entry(cycle, sources) 
				else:
					round2[key] = None #This marks that the value was overwritten (with a constant)
			roundSet = set(round2.values())
			if None in roundSet: roundSet.remove(None)

			if len(roundSet)>0:
				origins = set()
				for curSource in roundSet:
					origins |= curSource.listOrigins()
				self.generateEvent(origins, cycle.getTime(), cycle.getPC())
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
			result.append( (locations, "#%06X" % color, instrLocs))
			
		return result
		

	
class BackLink:
	""" A node in the data flow graph. Call toGraph() on the root node to 
	    get a list of nodes and edges.  """
	def __init__(self, cycle):
		self.cycle = cycle
		self.parents = []
	def link(self, newNode):
		self.parents.append(newNode)
	def __str__(self):
		if self.cycle is None:
			return "Final value"
		cycle = self.cycle
		return "%d/%08X %s" % (cycle.getTime(), cycle.getPC(), cycle.getDisasm())
	def toGraph(self):
		nodes = set()
		current = [self]
		edges = []
		while len(current):
			nextLevel = set()

			for curNode in current:
				nodes.add(str(curNode))
				for p in curNode.parents:
					edges.append((str(curNode), str(p)))
					nextLevel.add(p)
			current = nextLevel
		return nodes, edges


class BackwardDataFlow:
	""" This class is used to trace the origin of a certain value. It will
	    return the root (type 'BackLink') of a tree that describes how the value
	    was produced.  """
	#XXX: So short that we might not need a class for this
	def __init__(self, trace):
		self.trace = trace
	def follow(self, address, startTime, MAX_TRACE = 1000):
		first = BackLink(None)
		taintDict = { str(address): first }
		for cycle in self.trace.iterateCycles(startTime, delta = -1, maxCycles = MAX_TRACE):

			round2 = {}
			for key, sourceList in cycle.getEffects().items():
				#key is overwritten by values from data coming from <val>
				if not taintDict.has_key(key): continue
				oldVal = taintDict[key]
				del taintDict[key]

				#We taint all sources by the key
				for curSource in sourceList:
					round2[curSource] = BackLink(cycle)
					oldVal.link(round2[curSource])
			for k,v in round2.items():
				taintDict[str(k)] = v
		return first



