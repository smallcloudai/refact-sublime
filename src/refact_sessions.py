import sublime
import sublime_plugin
import re
import os 
import time
import traceback

from .utils import *
from .refact_lsp import LSP, get_language_id
from .refact_process import RefactProcessWrapper
from .phantom_state import PhantomState, PhantomInsertion
from .completion_text import get_nonwhitespace

class RefactSessionManager:

	def __init__(self):
		self.connection = None
		self.process = RefactProcessWrapper()
		self.connection = self.process.start_server()
		self.views = {}

	def restart_server(self):
		self.shutdown()
		self.start()

	def start(self):
		self.connection = self.process.start_server()
		
	def shutdown(self):
		if self.process and self.process.active:
			self.process.stop_server()
		for key, session in self.views.items():
			session.clear_completion()

	def get_view_id(self, view):
		if view.element() is None:
			return view.id()
		else:
			return "UI"

	def get_connection(self):
		if not self.process.active:
			self.process.start_server()
		return self.process.connection

	def get_session(self, view):
		view_id = self.get_view_id(view)
		if not view_id in self.views:
			self.views[view_id] = RefactSession(view, self.get_connection, view_id == "UI")
		return self.views[view_id]

class RefactSession:
	def __init__(self, view, connection, is_ui = False):
		self.completion_in_process = False
		self.session_state = 0
		self.version = 0
		self.view = view
		self.file_name = view.file_name() 
		if view.file_name() is None:
			if is_ui:
				self.file_name = os.path.abspath(os.sep) + "UI"
			else:
				self.file_name = os.path.abspath(os.sep) + str(time.time()) + "_" + str(view.id())

		self.phantom_state = PhantomState(view)
		self.connection = connection
		self.current_completion = None
		self.is_ui = is_ui;
		syntax = view.scope_name(get_cursor_point(view))
		file_type = syntax[(syntax.rindex(".") + 1):].strip()
		self.languageId = get_language_id(file_type)
		self.connection().load_document(self.file_name, get_text(self.view), self.languageId)
	
	def notify_document_update(self):
		if self.is_ui or self.phantom_state.update_step:
			return
		self.connection().did_change(self.file_name, self.version, get_text(self.view), self.languageId)

	def notify_close(self):
		if self.is_ui or self.phantom_state.update_step:
			return
		self.connection().did_close(self.file_name, self.version, get_text(self.view), self.languageId)

	def notify_save(self):
		if self.is_ui or self.phantom_state.update_step:
			return

		self.connection().did_save(self.file_name, self.version, get_text(self.view), self.languageId)

	def update_completion(self):
		if self.is_ui :
			return
		
		if self.is_paused():
			self.clear_completion()
			return
		
		if self.phantom_state.update_step:
			return

		if self.has_completion():
			self.phantom_state.update()
		if not self.completion_visible() and not self.completion_in_process:
			text = get_cursor_line(self.view)
			self.show_completions(text, [get_cursor_point(self.view)], len(text) == 0 or text.isspace())

	def completion_visible(self):
		return self.has_completion() and self.phantom_state.are_phantoms_visible()

	def has_completion(self):
		return not self.current_completion is None and len(self.current_completion) > 0 and not self.current_completion.isspace()

	def get_completion(self):
		return self.current_completion

	def clear_completion(self):
		self.session_state = self.session_state + 1
		self.current_completion = None
		self.phantom_state.clear_phantoms()

	def is_paused(self):
		s = sublime.load_settings("refact.sublime-settings")
		return s.get("pause_completion")
		
	def clear_completion_process(self):
		self.completion_in_process = False

	def show_completions(self, prefix, locations, multiline = False):
		if not self.phantom_state.update_step and not self.completion_in_process:
			self.completion_in_process = True
			sublime.set_timeout_async(lambda:self.show_completions_inner(self.session_state, prefix, locations, multiline))

	def set_phantoms(self, version, location, completion):
		if self.session_state != version or not self.is_position_valid(location):
			self.clear_completion_process()
			return

		text = get_line(self.view, location)
		rc = self.view.rowcol(location)
		if rc[1] < len(text.rstrip()):
			remainder = text[rc[1]:].rstrip()
			insertions = (completion).split(remainder)
			if len(insertions) > 1:
				next_text = insertions[1] if len(insertions) == 2 else "".join(insertions[1:])
				self.current_completion = completion
				self.phantom_state.set_new_phantoms([[PhantomInsertion(location, insertions[0]), PhantomInsertion(len(remainder), next_text)]])
		else:
			self.current_completion = completion
			self.phantom_state.set_new_phantoms([[PhantomInsertion(location, completion)]])
		self.clear_completion_process()

	def is_position_valid(self, location):
		rc = self.view.rowcol(location)
		text = get_line(self.view, location)
		after_cursor_text = text[rc[1]:].rstrip()
		if rc[1] < len(text):
			re_match = re.match(r"[:\s(){},.\"\'[\];]*", after_cursor_text)
			if not (re_match and len(re_match.group(0)) == len(after_cursor_text)):
				return False
		return True

	def show_completions_inner(self, version, prefix, locations, multiline = False):
		if version != self.session_state:
			self.clear_completion_process()
			return

		if self.is_ui or self.phantom_state.update_step:
			self.clear_completion_process()
			return

		if self.is_paused():
			self.clear_completion_process()
			return

		location = locations[0]
		if not self.is_position_valid(location):
			self.clear_completion_process()
			return

		rc = self.view.rowcol(location)

		if not prefix or prefix.isspace():
			pos_arg = (rc[0], 0)
		else:
			pos_arg = rc
		res = self.connection().get_completions(self.file_name, pos_arg, multiline)

		if res is None:
			self.clear_completion_process()
			return

		completions = res["choices"]

		if len(completions) > 0:
			completion = completions[0]['code_completion']
			if not completion or len(completion) == 0 or completion.isspace():
				self.clear_completion_process()
				return 

		text = get_line(self.view, location)
		suggestions = [text[:rc[1]] + s['code_completion'] for s in completions]
		sublime.set_timeout(lambda: self.set_phantoms(version, location, suggestions[0]))

	def accept_completion(self):
		if self.is_ui or self.phantom_state.update_step:
			return

		if self.completion_visible():
			text = self.get_completion()
			self.clear_completion()
			self.view.run_command("refact_replace_text", {'text': text})
