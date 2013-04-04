#This file contains the new version of the analysis functions.
#The script uses this whenever possible.
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
	""" Builds a dictionary that is used to replace registers with their
	values e.g. when calculating the memory addresses each instructions
	accesses"""
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


def processAffect(object):
	""" Undoes some miasm preprocessing to be able to see discern between different
	    parts of the same register."""
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
						target.size = 8
						resultingAffects.append(ExprAff(target, arg.arg))
		else:
			for curBit in xrange(0,32,8):
				target = ExprId(dest.name + "_%d" % curBit)
				resultingAffects.append(ExprAff(target, source))
			return [object]
		return resultingAffects
	else:
		return [object]


def getSliceBytes(srcObj, regs):
	if isinstance(srcObj, ExprSlice):
		if isinstance(srcObj.arg, ExprId):
			res = []
			assert srcObj.start % 8 == 0
			assert srcObj.stop % 8 == 0
			for i in xrange(srcObj.start, srcObj.stop, 8):
				res.append("%s_%d" % (srcObj.arg.name, i))
			return res
		else:
			raise ValueError

def getIdBytes(inputExpr, regs):
	if "_" in inputExpr.name: raise NotImplementedError
	return [("%s_%d" % (inputExpr.name, i)) for i in xrange(0,inputExpr.size,8)]


def getDataSource(sourceObject, regs, byteNum):
	""" Given an expression, returns the data sources that
	    can affect a certain byte of the output"""
	if isinstance(sourceObject, ExprSlice):
		bytes = getSliceBytes(sourceObject,regs)
	elif isinstance(sourceObject, ExprId):
		bytes = getIdBytes(sourceObject, regs)
	elif isinstance(sourceObject, int) or isinstance(sourceObject, ExprInt):
		if isinstance(sourceObject, int): #XXX: Hackish
			sourceObject = ExprInt(uint32(sourceObject))

		num = sourceObject.arg & 0xffffffffffffffff
		bytes =  []
		for i in xrange(0,sourceObject.get_size(),8):
			bytes.append("const_%d" % ((num>>i)&0xff))
	elif isinstance(sourceObject, ExprMem):
		startAddr = sourceObject.arg

		size = sourceObject.size/8
		addrExpr = expr_simp(sourceObject.arg.replace_expr(toReplaceDict(regs)))

		bytes = [(addrExpr.arg + i) for i in xrange(size)]	
	elif isinstance(sourceObject, ExprOp):

		res = []
		for curArg in sourceObject.args:
			res +=  getDataSource(curArg, regs, byteNum)
	#	print res, sourceObject.args
		return res
	elif isinstance(sourceObject, ExprCond):
		return getDataSource(sourceObject.src1, regs, byteNum) + \
		       getDataSource(sourceObject.src2, regs, byteNum)
	else:
		#print sourceObject.__class__
		raise ValueError, sourceObject.__class__
	return [bytes[byteNum]]

def listUnikeys(sourceObject, regs):
	""" Takes an object and lists its all bytes in unikey notation
	    (= integer representing the address of a byte in memory or REG_bitIndex )"""
	if isinstance(sourceObject, ExprMem):
		res = []
		startAddr = sourceObject.arg

		size = sourceObject.size/8
		addrExpr = expr_simp(sourceObject.arg.replace_expr(toReplaceDict(regs)))

		return [(addrExpr.arg + i) for i in xrange(size)]
	elif isinstance(sourceObject, ExprId):
		if "_" in sourceObject.name:
			assert sourceObject.size == 8
			return [sourceObject.name]
		size = sourceObject.size/8 
		return ["%s_%d" % (sourceObject.name,i*8) for i in xrange(size)]
	elif isinstance(sourceObject, ExprSlice):
		sliceBytes = getSliceBytes(sourceObject, regs)
		return sliceBytes
	#print sourceObject, sourceObject.__class__
	raise ValueError


def buildMatrix_new(affects, regs):
	result = {}
	for curAffect in affects:
		written =  listUnikeys(curAffect.dst, regs)
		for byteIndex in xrange(0, len(written)):
			#XXX: Put a switch for endianness?
			result[written[byteIndex]] = getDataSource(curAffect.src, regs, byteIndex)
			#print "to ", written[byteIndex], " ", result[written[byteIndex]]
	return result

