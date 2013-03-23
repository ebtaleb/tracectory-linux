import os
from elfesteem import *
from miasm.tools.pe_helper import *
from miasm.core.bin_stream import bin_stream, bin_stream_file
from collections import defaultdict
import miasm.arch.ia32_sem
from miasm.expression.expression_helper import *
from miasm.expression.expression import *
import miasm.expression.expression 
from miasm.arch.ia32_reg import *
from miasm.arch.ia32_arch import *
import pickle

from EffectAnalyzer import processAffect, convertToUnikey
from taint import *
from data_sources import FossileStream, Trace


def toReplaceDict(origRegs):
	result = {}
	result[miasm.arch.ia32_sem.eax] = ExprInt(uint32(origRegs["EAX"]))
	result[miasm.arch.ia32_sem.ebx] = ExprInt(uint32(origRegs["EBX"]))
	result[miasm.arch.ia32_sem.ecx] = ExprInt(uint32(origRegs["ECX"]))
	result[miasm.arch.ia32_sem.edx] = ExprInt(uint32(origRegs["EDX"]))
	result[miasm.arch.ia32_sem.esp] = ExprInt(uint32(origRegs["ESP"]))
	result[miasm.arch.ia32_sem.ebp] = ExprInt(uint32(origRegs["EBP"]))
	result[miasm.arch.ia32_sem.esi] = ExprInt(uint32(origRegs["ESI"]))
	result[miasm.arch.ia32_sem.edi] = ExprInt(uint32(origRegs["EDI"]))
	return result


#TODO: Separate reading and indexing

# Each location can be used for
# - read indexing (!)
# - write indexing
# - reading of value (!)
# - written

def getRead(affect):
	if isinstance(affect.src, ExprCond): return set([])
	if type(affect.src)==int: return set([])
	return affect.get_r()

def getWritten(affect):
	return affect.get_w()


def convertToKey(data, regs):
	"""Takes a miasm expression and the values for each register and transforms
	into a hashable object that uniquely represents the location (memory/reg) etc. """
	if isinstance(data, ExprId):
		#We have to expand this into separate bytes
		if "_" in data.name:
			return [data.name]

		res = []
		for i in xrange(0,data.size,8):
			res.append("%s_%d" % (data.name, i))
		return res
	elif isinstance(data,ExprMem):
		#print "Argument", data.arg
		#print data.arg.replace_expr(toReplaceDict(regs))

		size = data.size/8
		addrExpr = expr_simp(data.arg.replace_expr(toReplaceDict(regs)))

		return [(addrExpr.arg + i) for i in xrange(size)]

	else:
		print repr(data)
		raise ValueError
	raise ValueError, "Should never be reached"
	print data,repr(data)
	return data

def calcUnikeyRelations(affects, t, debug = False):
	# Loop through affects and transform this into a list
	# for each unikey of the unikeys that affected it
	# Returns a dictionary that maps each affected unikey
	# to those unikeys that were to used to produce the new
	# value at this unikey.
	result = defaultdict(set)
	for a in affects:
		readStuff = getRead(a)
		writtenStuff = getWritten(a)
		for w in writtenStuff:
			listOfLocationsWritten = convertToKey(w, t.regs)
			readSet = set()
			for curRead in readStuff:
				converted = convertToKey(curRead, t.regs)
				if debug:
					print a
					print curRead,converted
				readSet|= set(converted)

			#readSet = set([convertToKey(x, t.regs) for x in readStuff])
			for curWrite in listOfLocationsWritten:
				result[curWrite] |= readSet
	return result


def changeMatrixIterator(traceIterator, t, memorySpaceStream, newEngine = False, suppressErrors = False):
	""" A convenience wrapper that allows one to iterate directly
	through the affected locations. Performs the necessary disassembly
	and calls calcUnikeyRelations"""
	#TODO: We could cache this accross multiple invocations to improve performance
	affectCache = {}
	instrCache = {}
	for curTime, eip in traceIterator:
		if eip is None: continue

		#Analyze instruction
		if instrCache.has_key(eip):
			affects = affectCache[eip]
			instr = instrCache[eip]
		else:
			instr = asmbloc.dis_i(x86_mn,memorySpaceStream, eip, symbol_pool)
			origAffects =  get_instr_expr(instr, 123, [])
			affects = []
			for a in origAffects:
				affects += processAffect(a)
			affectCache[eip] = affects
			instrCache[eip] = instr

		if newEngine:
			try:
				changeMatrix = convertToUnikey(affects, t.regs)
			except:
				changeMatrix = None
				if not suppressErrors:
					raise
		else:
			changeMatrix = calcUnikeyRelations(affects, t)

		yield curTime, eip, instr, changeMatrix


from datastore.DataFlow import *
class MemoryHistory():
	def __init__(self, oldDB, newDB):
		self.oldDB = oldDB
		self.newDB = newDB
		self.trace = DataFlow(oldDB)
		self.newDF = DataFlow(newDB)
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


symbol_pool = asmbloc.asm_symbol_pool()




#A = TaintAnalyzer()
#BLOCK_START = 0x40305c
#BLOCK_LEN = 14
#BLOCK_START = 0x403064
#BLOCK_LEN = 51
#TA.mark(BLOCK_START, 0, BLOCK_LEN)


