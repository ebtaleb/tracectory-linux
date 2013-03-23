import os, sys
import struct
from elfesteem import *
from random import randint
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

#current = pickle.load(open("affect.p", "rb"))

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


def processWrite(object):
	print str(object)

def processAffect(object):
	if not isinstance(object, ExprAff): raise ValueError, "Expected ExprAff at processAffect"
	#Target 1: Strip the unnecessary slices

	dest = object.dst
	source = object.src
	if isinstance(dest, ExprId):
		#Is a register
		resultingAffects = []
		if isinstance(source,ExprCompose):
			for arg in source.args:
				#print "Bits %d - %d : %s" % (arg.start, arg.stop, arg.arg)
				#print arg.arg.__class__
				if isinstance(arg.arg, ExprSlice) and \
						arg.arg.start == arg.start and arg.arg.stop == arg.stop and \
						arg.arg.arg == dest:
					pass #We can ditch this
				else:
					assert arg.start%8 == 0
					assert arg.stop % 8 == 0
					for curBit in xrange(arg.start, arg.stop, 8):
						target = ExprId(dest.name + "_%d" % curBit)
						resultingAffects.append(ExprAff(target, arg.arg))
		else:
			for curBit in xrange(0,32,8):
				target = ExprId(dest.name + "_%d" % curBit)
				resultingAffects.append(ExprAff(target, source))
			return [object]
		return resultingAffects
	else:
		return [object]


def getSliceBytes(object, regs):
	if isinstance(object, ExprSlice):
		if isinstance(object.arg, ExprId):
			res = []
			assert object.start % 8 == 0
			assert object.stop % 8 == 0
			for i in xrange(object.start, object.stop, 8):
				res.append("%s_%d" % (object.arg.name, i))
			return res
		else:
			raise ValueError

def getIdBytes(inputExpr, regs):
	if "_" in inputExpr.name: raise NotImplementedError
	return [("%s_%d" % (inputExpr.name, i)) for i in xrange(0,inputExpr.size,8)]


def getDataSource(sourceObject, regs, byteNum):
	if isinstance(sourceObject, ExprSlice):
		bytes = getSliceBytes(sourceObject,regs)
	elif isinstance(sourceObject, ExprId):
		bytes = getIdBytes(sourceObject, regs)
	elif isinstance(sourceObject, int) or isinstance(sourceObject, ExprInt):
		num = sourceObject.arg & 0xffffffffffffffff
		bytes =  []
		for i in xrange(0,sourceObject.get_size(),8):
			bytes.append((num>>i)&0xff)
		return bytes
#	elif isinstance(sourceObject, ExprOp):
#		res = []
#		for arg in sourceObject.args:
#			res += getDataSource(arg, regs, byteNum)
#		return res
#	elif isinstance(sourceObject, ExprMem):
#		startAddr = sourceObject.arg
#
#		size = sourceObject.size/8
#		addrExpr = expr_simp(sourceObject.arg.replace_expr(toReplaceDict(regs)))
#
#		return [(addrExpr.arg + i) for i in xrange(size)]	
	else:
		print sourceObject.__class__
		raise ValueError, sourceObject.__class__
	return [bytes[byteNum]]

#XXX: What about if ExprSlice here
def listUnikeys(sourceObject, regs):
	if isinstance(sourceObject, ExprMem):
		res = []
		startAddr = sourceObject.arg

		size = sourceObject.size/8
		addrExpr = expr_simp(sourceObject.arg.replace_expr(toReplaceDict(regs)))

		return [(addrExpr.arg + i) for i in xrange(size)]
	elif isinstance(sourceObject, ExprId):
		#XXX: Should we bit- or byteindex
		size = sourceObject.size/8 
		return ["%s_%d" % (sourceObject.name,i*8) for i in xrange(size)]
	print sourceObject, sourceObject.__class__
	raise ValueError


def convertToUnikey(affects, regs):
	result = {}
	for curAffect in affects:
		written =  listUnikeys(curAffect.dst, regs)
		for byteIndex in xrange(0, len(written)):
			#XXX: Put a switch for endianness
			result[written[byteIndex]] = getDataSource(curAffect.src, regs, byteIndex)
			#print "to ", written[byteIndex], " ", result[written[byteIndex]]
	return result

