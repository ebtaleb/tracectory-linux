# This file contains the old version of the code that builds a dictionary
# mapping incoming unikeys to those unikeys that are modified.
# This does not map the effects very precisely, but is still used
# when the new version cannot handle the instruction. 
#
# Unikey = (memory or register)
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

def buildMatrix_old(affects, regs, debug = False):
	# Loop through affects and transform this into a list
	# for each unikey of the unikeys that affected it
	# Returns a dictionary that maps each affected unikey
	# to those unikeys that were to used to produce the new
	# value at this unikey.
	result = defaultdict(set)
	for a in affects:
		if isinstance(a.src, ExprOp) and a.src.op == "^": # this tries to fix xor eax,eax to cut the chain
			a.src = expr_simp(a.src)
		readStuff = getRead(a)
		writtenStuff = getWritten(a)
		for w in writtenStuff:
			listOfLocationsWritten = convertToKey(w, regs)
			readSet = set()
			for curRead in readStuff:
				converted = convertToKey(curRead, regs)
				if debug:
					print a
					print curRead,converted
				readSet|= set(converted)

			#readSet = set([convertToKey(x, t.regs) for x in readStuff])
			for curWrite in listOfLocationsWritten:
				result[curWrite] |= readSet
	return result





symbol_pool = asmbloc.asm_symbol_pool()
