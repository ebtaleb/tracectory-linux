import cherrypy
import os
import json
from threading import Lock
from time import time as systemtime
from TargetTrace import TargetTrace
from taint import *

traces  = {}
for curDb in os.listdir("db/"):
	if curDb.endswith("_combined"):
		name = curDb[:curDb.find("_combined")]
		traces[name] = TargetTrace(name)

if len(traces) == 0:
	print >>sys.stderr, "No traces found in db/, no point in starting the GUI"
	print >>sys.stderr, "Create traces using the preprocess tools (see wiki for details)"
	os.sys.exit(1)

defaultTrace  = traces.keys()[0]

def parseExpr(x): return int(x, 16)

def getTrace():
	try:
		return  cherrypy.session['trace']
	except KeyError:
		cherrypy.session['trace'] = traces[defaultTrace]
		return cherrypy.session['trace']

#Crude input validation here, we'll just crash if the input does not 
#coerse to int

class CpuApi(object):
	@cherrypy.expose
	def getInstructions(self, time):
		time = int(time)
		startTime = max(0,time-10)
		target = getTrace()
		t = target.cycleFactory

		dump = dump2 = "{}"
		with target.getLock():
			result = {'disasm' : []}

			for cycle in t.iterateCycles(startTime):
				if cycle.getTime() > time: break
				cleanAsm = cycle.getDisasm()
				while "  " in cleanAsm:
					cleanAsm = cleanAsm.replace("  "," ")
				result['disasm'].append((cycle.getTime(), cycle.getPC(), cleanAsm))
			
			if t.getCycle(time) is not None: dump = t.getCycle(time).jsonDump()
		result['dump'] = "%s" % dump
		return json.dumps(result)

class MemoryApi(object):
	@cherrypy.expose
	def getMemJson(self, address, time):
		if not time.isdigit():
			return json.dumps({'error' : "Time format not recognized!"})

		timeSlot = int(time)
		address = int(address)
		res = {}
		res['bytes'] = []
		res['times'] = []


		target = getTrace()
		mh = target.getMemoryHistory()

		with target.getLock():
			for addr in xrange(address,address + 8*6):
				result = mh.getWithTime(addr, timeSlot)
				if result is None:
					res['bytes'].append(-1)
					res['times'].append(-1)
				else:
					res['bytes'].append(result[0])
					res['times'].append(result[1])
		return json.dumps(res)
	@cherrypy.expose
	def getRW(self, time):
		target = getTrace()
		time = int(time)
		result, reads, writes = {}, [], []
		with target.getLock():
			mh = target.getMemoryHistory()
			dfTracer = target.getCycleFactory()
			cycle = dfTracer.getCycle(time)
			if cycle is None:
				return json.dumps( { 'status' : 'error' } )
			listOfReads, listOfWrites = cycle.getMemoryRW()
			for read in listOfReads:	
				reads.append( { 'addr' : read,
						'prevWrite' : mh.previousWrite(read, time)
					      })

			for write in listOfWrites:
				writes.append( { 'addr' : write,
						 'nextRead' : mh.nextRead(write, time)
						})
			
		return json.dumps( { 'status' : 'ok', 'reads' : reads, 'writes' : writes } )

	@cherrypy.expose
	def wholeProgram(self, timeResolution, addrResolution, startBlock, startTime, endTime, startAddr, endAddr):
		target = getTrace()
		timeResolution = int(timeResolution)
		addrResolution = int(addrResolution)
		startBlock = int(startBlock)

		startTime = int(startTime)
		endTime   = int(endTime)
		startAddr = int(startAddr)
		endAddr = int(endAddr)
		if startTime == -1: startTime = None
		if endTime == -1: endTime = None
		if startAddr == -1: startAddr = None
		if endAddr == -1: endAddr = None
		with target.getLock():
			mh = target.getMemoryHistory()
			res = mh.getOverview(timeResolution = timeResolution, addrResolution = addrResolution, startBlock = startBlock,
				startTime = startTime, endTime = endTime, startAddr = startAddr, endAddr = endAddr)
			return res

class TaintApi(object):
	@cherrypy.expose
	def forwardTaint(self, address, time):
		target = getTrace()
		address = int(address)
		time = int(time)
		result = {}
		dataLen = 3*16 + 1
		with target.getLock():
			t = target.getCycleFactory()
			mh = target.getMemoryHistory()
			analyzer = ForwardTaintAnalyzer()
			analyzer.mark(address, 0, dataLen)
			res = analyzer.analyze(t, time)
			result['graph'] = analyzer.toGraph(res)
			result['data'] = [mh.get(x, time) for x in xrange(address,address+dataLen)]
		return json.dumps(result, indent = 4)
	@cherrypy.expose
	def dataflow(self, time, address):
		address = int(address)
		time = int(time)
		target = getTrace()
		t = target.getCycleFactory()
		with target.getLock():
			startTime = systemtime()
			df = BackwardDataFlow(t)
			root = df.follow(address, time, 4000)
			nodes, edges = root.toGraph()
			endTime = systemtime()

		graph = "digraph G {\n"
		graph += "/* Took %f seconds */\n" % (endTime-startTime)
		#XXX: We're cheating by using set here, should move into proper engine
		for e in set(edges):
			graph+= '"%s" -> "%s"\n' % (e[1], e[0])
		graph += "}";
		
		return json.dumps({ 'graph' : graph } )

class Views(object):
	@cherrypy.expose
	def renderDataflow(self, address, time):
		s = open(os.path.dirname(os.path.realpath(__file__)) + "/dataflow.html").read()
		s = s.replace("%ADDR%", str(int(address)))
		s = s.replace("%TIME%", str(int(time)))
		return s

class GuiServer(object):
	cpu = CpuApi()
	memory = MemoryApi()
	taint = TaintApi()
	view = Views()
	def index(self):
		raise cherrypy.HTTPRedirect("static/main.html")
	def getInfo(self):
		target = getTrace()
		with target.getLock():
			return json.dumps( { 
				'maxTime' : target.getMaxTime(),
				'memDumpAddr' : target.getMemDumpAddr(),
				'infoHtml' : target.getInfoHtml(),
				'traces' : traces.keys()
			} );
	def loadTrace(self, trace):
		if not traces.has_key(trace):
			return json.dumps( {'status' : 'error' } )
		cherrypy.session['trace'] = traces[trace]

		return json.dumps( {'status' : 'ok' } )

	def memoryAccessEvents(self, address, bytes, time, cycles, compress):
		target = getTrace()
		address = parseExpr(address)
		time = int(time)
		bytes = int(bytes)
		memRange = range(address, address + bytes)
		cycles = int(cycles)
		compress = bool(int(compress))

		rangeSize = len(memRange)
		#We trust that there are not more than one million memory accesses
		complexity = rangeSize * 20 + cycles
		if complexity > 500000:
			return json.dumps({ 'status' : 'error',
			'error' : 'Estimated complexity exceeds server bounds, rejected!'})
			

		with target.getLock():
			mh = target.getMemoryHistory()
			evts = mh.iterMemoryEvents(memRange, time, time + cycles, groupByTime=True)
			evts, newIndexes = mh.memoryGraph(list(evts), compress = compress, minAddr = min(memRange))

		if compress: rangeSize = len(newIndexes)

		return json.dumps(
			{'status' : 'ok',
		 	 'graph' : evts,
			 'rangeSize' : rangeSize
			}, indent = 4)

	memoryAccessEvents.exposed = True
	index.exposed = True
	getInfo.exposed = True
	loadTrace.exposed = True

current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/static': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(current_dir, 'static_html')}}

#cherrypy.server.socket_host = "0.0.0.0"
cherrypy.config.update( {"tools.sessions.on": True,
			"tools.sessions.timeout": 60 })
cherrypy.quickstart(GuiServer(), config = conf)

