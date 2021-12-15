from datetime import datetime
import sys

class Log:
	INFO = "INFO"
	WARN = "WARN"
	ERR  = " ERR"

	def __init__(self):
		pass

	def write(self, severity, msg):
		tstr = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
		logstr = f"[{tstr}] [{severity}]: {msg}"

		if severity == self.INFO:
			print(logstr)
		else:
			print(logstr, file = sys.stderr)

	def info(self, msg):
		self.write(self.INFO, msg)
	def warn(self, msg):
		self.write(self.WARN, msg)
	def err(self, msg):
		self.write(self.ERR, msg)


	def fail(self, estr, e):
		self.write(self.ERR, f"{str}: " + str(e))
		raise e
		sys.exit(1)
