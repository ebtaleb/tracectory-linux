import cherrypy
import os
import json
from threading import Lock
from time import time as systemtime
from session import TargetTrace
from datastore.DataFlow import *
from taint import *

traces = {
	't206'     : TargetTrace("t206_timed"),
	'memcrypt' : TargetTrace("memcrypt"),
	'formatstring' : TargetTrace("formatstring"),
}

traces['memcrypt'].memDumpAddr = 0x404050;
traces['t206'].memDumpAddr = 2771222;
traces['formatstring'].memDumpAddr = 0x4825A0;
defaultTrace = "memcrypt"

def parseExpr(x):
	return int(x, 16)

def getTrace():
	try:
		return  cherrypy.session['trace']
	except KeyError:
		cherrypy.session['trace'] = traces[defaultTrace]
		return cherrypy.session['trace']

class CpuApi(object):
	@cherrypy.expose
	def getInstructions(self, time):
		time = int(time)
		startTime = max(0,time-10)
		target = getTrace()
		t = target.getDataflowTracer()
		with target.getLock():
			t.seek(startTime)
			result = {'disasm' : []}

			for data in t.iterate():
				curTime, eip, instr, changeMatrix = data
				cleanAsm = instr
				while "  " in cleanAsm:
					cleanAsm = cleanAsm.replace("  "," ")
				result['disasm'].append((curTime, eip, cleanAsm))
				if data[0] == time: break
			t.seek(time)
			newT = target.getDataflowTracer(new=True)
			newT.seek(time)
			dump = json.dumps(json.loads(t.dumpState()), indent=4)
			dump2 = json.dumps(json.loads(newT.dumpState()), indent=4)
		result['dump'] = "%s" % dump
		result['dump2'] = "%s" % dump2
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
		result = {}
		reads = []
		writes = []
		with target.getLock():
			mh = target.getMemoryHistory()
			dfTracer = target.getDataflowTracer()
			time, eip, disasm, matrix = dfTracer.getAt(time)
			listOfReads, listOfWrites = mh.getRW(matrix)
			for read in listOfReads:	
				reads.append( { 'addr' : read,
						'prevWrite' : mh.previousWrite(read, time)
					      })

			for write in listOfWrites:
				writes.append( { 'addr' : write,
						 'nextRead' : mh.nextRead(write, time)
						})
			
		return json.dumps( { 'reads' : reads, 'writes' : writes } )

class TaintApi(object):
	@cherrypy.expose
	def forwardTaint(self, address, time):
		target = getTrace()
		address = int(address)
		time = int(time)
		result = {}
		dataLen = 3*16 + 1
		with target.getLock():
			t = target.getDataflowTracer()
			mh = target.getMemoryHistory()
			analyzer = ForwardTaintAnalyzer()
			#analyzer.mark(0x403064, 0, 3*16 + 1)
			analyzer.mark(address, 0, dataLen)
			t.seek(time)
			res = analyzer.analyze(t)
			result['graph'] = analyzer.toGraph(res)
			result['data'] = [mh.get(x, time) for x in xrange(address,address+dataLen)]
		return json.dumps(result, indent = 4)
	@cherrypy.expose
	def dataflow(self, time, address):
		address = int(address)
		time = int(time)
		target = getTrace()
		t = target.getDataflowTracer()
		with target.getLock():
			startTime = systemtime()
			df = BackwardDataFlow(t)
			root = df.follow(address, time, 4000)
			nodes, edges = root.dump()
			endTime = systemtime()

		graph = "digraph G {\n"
		graph += "/* Took %f seconds */\n" % (endTime-startTime)
		#XXX: We're cheating by using set here, should move into proper engine
		for e in set(edges):
			graph+= '"%s" -> "%s"\n' % (e[1], e[0])
		graph += "}";
		
		return json.dumps({ 'graph' : graph } )

class GuiServer(object):
	cpu = CpuApi()
	memory = MemoryApi()
	taint = TaintApi()
	def index(self):
		raise cherrypy.HTTPRedirect("static/main.html")
	def getInfo(self):
		target = getTrace()
		with target.getLock():
			return json.dumps( { 
				'maxTime' : target.getMaxTime(),
				'memDumpAddr' : target.getMemDumpAddr(),
				'infoHtml' : target.getInfoHtml()
			} );
	def loadTrace(self, trace):
		if not traces.has_key(trace):
			return json.dumps( {'status' : 'error' } )
		cherrypy.session['trace'] = traces[trace]

		return json.dumps( {'status' : 'ok' } )

	def memoryAccessEvents(self, address, bytes, time, cycles):
		target = getTrace()
#		address = int(address)
#		time = int(time)
		address = parseExpr(address)
		time = int(time)
		bytes = int(bytes)
		memRange = range(address, address + bytes)
		cycles = int(cycles)

		n = len(memRange)
		#We trust that there are not more than one million memory accesses
		complexity = n * 20 + cycles
		if complexity > 500000:
			return json.dumps({ 'status' : 'error',
			'error' : 'Estimated complexity exceeds server bounds, rejected!'})
			

		with target.getLock():
			mh = target.getMemoryHistory()
			#evts = mh.listMemoryEvents(range(0x404050,0x404050 + 16), 0, 1000)
			evts = mh.listMemoryEvents(memRange, time, time + cycles)
		return json.dumps(
			{'status' : 'ok',
		 	 'graph' : evts,
			 'rangeSize' : len(memRange)
			}, indent = 4)
	def getReadsAndWrites(self, time):
		time = int(time)
	

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

