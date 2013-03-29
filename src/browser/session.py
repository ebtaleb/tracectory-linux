import leveldb
from datastore.DataFlow import DataFlow
import os
from MemoryHistory import *
class TargetTrace:
	def __init__(self, saveName):
		self.oldDB = leveldb.LevelDB("db/%s_oldEngine" % saveName)
		self.newDB = leveldb.LevelDB("db/%s_newEngine" % saveName )
		self.dataflowTrace = DataFlow(self.oldDB)
		self.saveName = saveName
		self.dataflowTraceNew = DataFlow(self.newDB)
		self.memDumpAddr = 1
		self.mh = MemoryHistory(self)
	def getMaxTime(self):
		return int(self.oldDB.Get("maxTime"))	
	def getDataflowTracer(self, new = False):
		if not new:
			return self.dataflowTrace
		else:
			return self.dataflowTraceNew
	def getMemDumpAddr(self):
		return self.memDumpAddr
	def getDB(self, which):
		if which == "old":
			return self.oldDB
		elif which == "new":
			return self.newDB
		else:
			raise ValueError
	def getInfoHtml(self):
		filename = "db/%s_info.html" % self.saveName
		if not os.path.exists(filename): return "No info"
		return open(filename).read()

	def getMemoryHistory(self):
		return self.mh
