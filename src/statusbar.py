
import sublime

class StatusBar:
	def __init__(self):
		self.update_statusbar("ok")
		self.status_loop()
		self.icons = [u"◐", u"◓", u"◑", u"◒"]
		self.current_icon = 0

	def status_loop(self):
		display = ""

		if self.status == "error":
			display = '⛔refact.ai:' + self.msg
		elif self.status == "ok":
			display = "refact.ai"
		elif self.status == "loading":
			display = self.icons[self.current_icon] + "refact.ai"
			self.current_icon = (self.current_icon + 1 ) % len(self.icons)

		sublime.status_message(display)
		sublime.set_timeout(self.status_loop, 100)

	def update_statusbar(self, status, msg = ""):
		self.status = status
		self.msg = msg
