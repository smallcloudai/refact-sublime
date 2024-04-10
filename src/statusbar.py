import sublime

class StatusBar:
	def __init__(self):
		self.update_statusbar("ok")
		self.status_loop()
		self.icons = [u"◐", u"◓", u"◑", u"◒"]
		self.current_icon = 0
		self.duration = 0

	def status_loop(self):
		display = ""
		if self.status == "error":
			display = '⛔refact.ai:' + self.msg
		elif self.status == "pause":
			display ="⏸️ refact.ai"
		elif self.status == "ok":
			display = "refact.ai"
		elif self.status == "loading":
			display = self.icons[self.current_icon] + "refact.ai"
			self.current_icon = (self.current_icon + 1 ) % len(self.icons)

		sublime.status_message(display)
		if self.duration > 0 or self.status == "loading":
			if self.duration > 0:
				self.duration = self.duration - 1
		sublime.set_timeout(self.status_loop, 100)

	def update_statusbar(self, status, msg = ""):
		self.status = status
		self.msg = msg
		self.duration = 5
		self.status_loop()

	def handle_err(self, err):
		if self.status == "pause":
			return

		if not isinstance(err, str):
			if hasattr(err, 'message'):
				err = err.message
			else:
				err = str(err)
		self.update_statusbar("error", msg = str(err))