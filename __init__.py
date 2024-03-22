import sublime
import sublime_plugin
import subprocess
import os
from refact.src.utils import *
from refact.src.refact_process import RefactProcessWrapper
from refact.src.refact_sessions import RefactSessionManager, RefactSession

start_refact = False
refact_session_manager = None

class RefactAutocomplete(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		if start_refact:
			refact_session_manager.get_session(view).show_completions(prefix, locations)

	def on_modified(self, view):
		if not start_refact:
			return

		session = refact_session_manager.get_session(view)
		session.notify_document_update()
		session.update_completion()

	def on_close(self, view):
		if not start_refact:
			return

		session = refact_session_manager.get_session(view)
		session.notify_close()

	def on_post_save(self, view):
		if not start_refact:
			return

		session = refact_session_manager.get_session(view)
		session.notify_save()
	
	def on_query_context(self, view, key, operator, operand, match_all):
		if start_refact:
			if key == "refact.show_completion":
				return refact_session_manager.get_session(view).completion_visible()

	def on_post_text_command(self, view, command_name, args):
		if start_refact:
			session = refact_session_manager.get_session(view)
			if command_name == "insert" and args['characters'] == '\n':
				session.clear_completion()
				cursor_point = get_cursor_point(view)
				session.show_completions(get_cursor_line(view), [cursor_point], True)

	def on_text_command(self, view, command_name, args):
		if start_refact:
			session = refact_session_manager.get_session(view)
			if command_name == "commit_completion":
				if not session.get_completion() is None:
					session.accept_completion()
					return ["noop"]
			if command_name == "auto_complete":
				session.accept_completion()
			elif command_name == "insert" and args['characters'] == '\t':
				session.accept_completion()
			elif command_name == "reindent":
				session.accept_completion()
			elif command_name == "hide_popup":
				session.clear_completion()
			# elif command_name == "left_delete" or command_name == "right_delete":
	
			# 	session.clear_completion()
			elif command_name == "move" or command_name == "move_to":
				session.clear_completion()
			elif command_name == "drag_select":
				session.clear_completion()

def restart_server():
	global refact_session_manager 
	
	if refact_session_manager:
		s = sublime.load_settings("refact.sublime-settings")
		pause_completion = s.get("pause_completion", False)
		
		if not pause_completion:
			refact_session_manager.restart_server()

def plugin_loaded():
	global refact_session_manager 
	global start_refact
	s = sublime.load_settings("refact.sublime-settings")
	pause_completion = s.get("pause_completion", False)
	s.add_on_change("restart_server", restart_server)
	if pause_completion:
		sublime.status_message("⏸️ refact.ai")
	else:
		refact_start()

def get_start_refact():
	print("get_start_refact", start_refact)
	return start_refact

def refact_start():
	global refact_session_manager 
	global start_refact
	if refact_session_manager:
		refact_session_manager.start()
	else:
		refact_session_manager = RefactSessionManager(get_start_refact)
	start_refact= True

class RefactStartCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		refact_start()
		
class RefactStopCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global start_refact
		start_refact= False
		refact_session_manager.get_session(self.view).clear_completion()
		
class RefactAddTextCommand(sublime_plugin.TextCommand):
	def run(self, edit, text = '', position = None):
		view = self.view
		position = position if not position is None else view.sel()[0].b
		cursor_position = self.view.rowcol(self.view.sel()[0].b)
		line = view.line(position)
		self.view.insert(edit, line.b, text)
		point = self.view.text_point(cursor_position[0], cursor_position[1], clamp_column = True)
		set_cursor_position(self.view, sublime.Region(point, point))

class RefactClearSpaceCommand(sublime_plugin.TextCommand):
	def run(self, edit, position = None):
		if position is None:
			return
		view = self.view
		cursor_position = self.view.rowcol(self.view.sel()[0].b)

		line = view.line(position)
		text = get_line(view, position)
		if len(text) > 0 and text[len(text) - 1].isspace():
			region = sublime.Region(line.b - 1, line.b)
			view.erase(edit, region)

		point = self.view.text_point(cursor_position[0], cursor_position[1], clamp_column = True)
		set_cursor_position(self.view, sublime.Region(point, point))

class RefactReplaceTextCommand(sublime_plugin.TextCommand):
	def run(self, edit, text = '', position = None):
		view = self.view
		position = position if not position is None else view.sel()[0].b
		line  = view.line(position)
		view.replace(edit, sublime.Region(line.a, line.b), '')
		view.insert(edit, line.a, text)

class RefactAcceptCompletion(sublime_plugin.TextCommand):
	def run(self, edit):
		refact_session_manager.get_session(self.view).accept_completion()

class RefactPause(sublime_plugin.TextCommand):
	def run(self, edit):
		global start_refact
		s = sublime.load_settings("refact.sublime-settings")
		pause_status = s.get("pause_completion", False)
		pause_status = not pause_status
		start_refact = not pause_status
		s.set("pause_completion", pause_status)
		sublime.save_settings("refact.sublime-settings")

		if not pause_status and refact_session_manager is None:
			refact_start()
		else:
			if refact_session_manager:
				refact_session_manager.shutdown()

class RefactClearCompletion(sublime_plugin.TextCommand):
	def run(self, edit):
		refact_session_manager.get_session(self.view).clear_completion()
