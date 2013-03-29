import cherrypy
import os
import json
from threading import Lock
from time import time as systemtime

from session import TargetTrace
from MemoryHistory import *


traces = {
	't206'     : TargetTrace("t206_timed"),
	'memcrypt' : TargetTrace("memcrypt"),
	'formatstring' : TargetTrace("formatstring"),
}

traces['memcrypt'].memDumpAddr = 0x404050;
traces['t206'].memDumpAddr = 2771222;

lock = Lock()
class GuiServer(object):
	def index(self):
		raise cherrypy.HTTPRedirect("static/main.html")
	def getInfo(self):
		target = cherrypy.session['trace']
		return json.dumps( { 

		'maxTime' : target.getMaxTime(),
		'memDumpAddr' : target.getMemDumpAddr()
		} );
	def getMemJson(self, address, time):
		if not time.isdigit():
			return json.dumps({'error' : "Time format not recognized!"})

		timeSlot = int(time)
		address = int(address)
		res = {}
		res['bytes'] = []
		res['times'] = []


		target = cherrypy.session['trace']

		mh = MemoryHistory(target)

		with lock:
			for addr in xrange(address,address + 8*6):
				result = mh.getWithTime(addr, timeSlot)
				if result is None:
					res['bytes'].append(-1)
					res['times'].append(-1)
				else:
					res['bytes'].append(result[0])
					res['times'].append(result[1])
		return json.dumps(res)
	def getInstructions(self, time):
		time = int(time)
		startTime = max(0,time-10)
		target = cherrypy.session['trace']
		t = target.getDataflowTracer()
		with lock:
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
	def dataflow(self, time, address):
		address = int(address)
		time = int(time)
		target = cherrypy.session['trace']
		t = target.getDataflowTracer()
		with lock:
			startTime = systemtime()
			df = BackwardDataFlow(t)
			root = df.follow(address, time, 300)
			nodes, edges = root.dump()
			endTime = systemtime()

		graph = "digraph G {\n"
		graph += "/* Took %f seconds */\n" % (endTime-startTime)
		#XXX: We're cheating by using set here, should move into proper engine
		for e in set(edges):
			graph+= '"%s" -> "%s"\n' % (e[1], e[0])
		graph += "}";
		
		return json.dumps({ 'graph' : graph } )
	def loadTrace(self, trace):
		if not traces.has_key(trace):
			return json.dumps( {'status' : 'error' } )
		cherrypy.session['trace'] = traces[trace]

		return json.dumps( {'status' : 'ok' } )

	def forwardTaint(self, address, time):
		target = cherrypy.session['trace']
		address = int(address)
		time = int(time)
		result = {}
		dataLen = 3*16 + 1
		with lock:
			t = target.getDataflowTracer()
			mh = MemoryHistory(target)
			analyzer = ForwardTaintAnalyzer()
			#analyzer.mark(0x403064, 0, 3*16 + 1)
			analyzer.mark(address, 0, dataLen)
			t.seek(time)
			res = analyzer.analyze(t)
			result['graph'] = analyzer.toGraph(res)
			result['data'] = [mh.get(x, time) for x in xrange(address,address+dataLen)]
		return json.dumps(result, indent = 4)
	def dbg(self, address):
		target = cherrypy.session['trace']
#		address = int(address)
#		time = int(time)
		with lock:
			mh = MemoryHistory(target)
			#evts = mh.listMemoryEvents(range(0x404050,0x404050 + 16), 0, 1000)
			evts = mh.listMemoryEvents(range(0x2a48e0, 0x2a4900 + 16*4), 0, 60000)
		return json.dumps(evts, indent = 4)
	

	dbg.exposed = True
	index.exposed = True
	getMemJson.exposed = True
	getInfo.exposed = True
	getInstructions.exposed = True
	dataflow.exposed = True
	loadTrace.exposed = True
	forwardTaint.exposed = True

current_dir = os.path.dirname(os.path.abspath(__file__))
conf = {'/static': {'tools.staticdir.on': True,
                      'tools.staticdir.dir': os.path.join(current_dir, 'static_html')}}

#cherrypy.server.socket_host = "0.0.0.0"
cherrypy.config.update( {"tools.sessions.on": True,
			"tools.sessions.timeout": 60 })
cherrypy.quickstart(GuiServer(), config = conf)

