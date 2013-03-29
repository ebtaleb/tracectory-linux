import leveldb
from datastore.DataFlow import DataFlow

class TargetTrace:
	def __init__(self, saveName):
		self.oldDB = leveldb.LevelDB("db/%s_oldEngine" % saveName)
		self.newDB = leveldb.LevelDB("db/%s_newEngine" % saveName )
		self.dataflowTrace = DataFlow(self.oldDB)
		self.dataflowTraceNew = DataFlow(self.newDB)
		self.memDumpAddr = 1
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
