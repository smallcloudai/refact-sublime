import sublime
import sublime_plugin
import subprocess
import threading
import os
from .refact_lsp import LSP
from .statusbar import StatusBar

class RefactProcessWrapper():
	def __init__(self):
		self.connection = None
		self.active = False
		self.statusbar = StatusBar()

	def get_server_path(self):
		return os.path.join(sublime.packages_path(), "refact", "server", "refact-lsp")
	
	def get_server_commands(self):
		s = sublime.load_settings("refact.sublime-settings")

		address_url = s.get("address_url", "")
		address_url = address_url if len(address_url) > 0 else "Refact"
		api_key = s.get("api_key", "")
		options = [
			self.get_server_path(),
			"--address-url",  address_url,
			"--api-key", api_key,
			"--lsp-stdin-stdout", "1",
		]

		telemetry_basic = s.get("telemetry_basic", False)
		if telemetry_basic:
			options.append("--basic-telemetry")

		telemetry_code_snippets = s.get("telemetry_code_snippets", False)
		if telemetry_basic:
			options.append("--snippet-telemetry")

		return options

	def start_server(self):
		self.active = True
		server_cmds = self.get_server_commands()
		self.process = subprocess.Popen(server_cmds, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr=subprocess.PIPE, shell=False)

		self.statusbar.update_statusbar("ok")
		if not self.connection is None:
			self.connection.shutdown()

		self.connection = LSP(self.process, self.statusbar)

	def stop_server(self):
		self.connection.shutdown()
		self.process.terminate()
		self.statusbar.update_statusbar("pause")
		
