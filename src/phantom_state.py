from enum import Enum
import traceback
import sublime
import sublime_plugin
import html
from .utils import *
from .completion_text import get_completion_text, get_nonwhitespace
from dataclasses import dataclass
from typing import NamedTuple

Direction = Enum('Direction', ['inline', 'previous'])

class PhantomInsertion(NamedTuple):
	location: int
	text: str

class PhantomSeed():
	def __str__(self):
		return "PhantomSeed(position, text, version):" + str(self.position) + " " + self.text + " " + str(self.version)
	def __init__(self, view, position, text):
		self.position = position
		self.text = text
		self.version = view.change_id()
		self.line = view.rowcol(position)[0]

	def get_line(self, view):
		return view.line(view.transform_region_from(sublime.Region(self.position, self.position), self.version))

class Seed():
	def __str__(self):
		if self.is_empty():
			return "Seed:is_empty=True"
		else:
			return "Seed(cursor_phantom; next_inline_phantom, next_line_phantom): " + str(self.cursor_phantom) + "; " + str(self.next_inline_phantom) + "; " + str(self.next_line_phantom)

	def __init__(self, view, phantom_block):
		text = phantom_block[0].text
		newline_index = text.find('\n')
		first_line_end = newline_index if newline_index > 0 else len(text)
		first_line = text[:first_line_end]
		first_location = phantom_block[0].location
		self.cursor_phantom  = self.create_phantom(view, first_location, first_line)

		if len(phantom_block) > 1 and len(phantom_block[1].text) > 0:
			self.next_inline_phantom = self.create_phantom(view, phantom_block[1].location, phantom_block[1].text)
		else:
			self.next_inline_phantom = None

		if newline_index > 0:
			rest_text = text[newline_index:]
			self.next_line_phantom = self.create_phantom(view, first_location, rest_text)
		else:
			self.next_line_phantom = None
		
		self.empty = (not self.cursor_phantom or len(self.cursor_phantom.text) == 0) and not self.next_inline_phantom and not self.next_line_phantom

	def is_cursor_on_line(self, view, line):
		return self.cursor_phantom.line == view.rowcol(line.b)[0]

	def create_phantom(self, view, position, text):
		return PhantomSeed(view, position, text)

	def is_empty(self):
		return getattr(self, "empty", None)

	def get_cursor_text(self):
		return self.cursor_phantom.text

class AddedSpace():
	def __init__(self, view, popup_type):
		self.direction = AddedSpace.get_direction(popup_type)
		self.version = view.change_id()
		self.position = AddedSpace.get_postion(view, self.direction)
		self.add_space(view)

	def get_postion(view, direction):
		cursor_point = get_cursor_point(view)
		if direction == Direction.previous:
			return get_previous_line(view, cursor_point)
		else:
			return view.line(cursor_point)

	def get_direction(popup_type):
		return Direction.previous if popup_type else Direction.inline

	def get_line(self, view):
		return view.line(view.transform_region_from(self.position, self.version))

	def on_same_line(self, view, popup_type):
		new_direction = AddedSpace.get_direction(popup_type)
		new_position = AddedSpace.get_postion(view, new_direction)
		old_position = self.get_line(view)
		return new_position.intersects(old_position)
	
	def add_space(self, view):
		view.run_command("refact_add_text", {'text': ' ', 'position': self.get_line(view).b})
	
	def remove_space(self, view):
		view.run_command("refact_clear_space", {'position' : self.get_line(view).b})

class PhantomState:
	def __init__(self, view):
		self.phantomSet = sublime.PhantomSet(view)
		self.added_space = None
		self.seeds = []
		self.view = view
		self.update_step = False
		self.phantoms_visible = False
		s = sublime.load_settings("Preferences.sublime-settings")
		self.tab_size = get_tab_size()

	invisibleDiv = """
	<body id="invisible-div">
		<style>
			html, body {
				line-height: 0;
				margin-top: 0;
			}
		</style>
	</body>
	"""

	def create_inline_template(self, text):
		return """
		<body id="inline-div">
			<style>
				html, body {
					background-color: transparent;
					color : grey;
					position: relative;
					text-align: left;
					margin-top: 0;
					line-height: 0;
				}
			</style>

			""" + self.html_prepare(text) + """
		</body>
		"""
	
	def create_annotation_template(self, text):
		return """
		<body id="line-annotation">
			<style>
				html, body {
					color : grey;
					background-color: color(var(--background));
					display:inline;
				}
			</style>

			""" + self.html_prepare(text) + """
		</body>
		"""

	def html_prepare(self, s):
		s = s.replace('\t', ' ' * self.tab_size)
		res = "<br>".join([html.escape(s) for s in s.split('\n')])
		res = res.replace(" ", "&nbsp;")
		return res

	def create_inline_phantom(self, a, b, text):
		region = sublime.Region(a,b)
		return sublime.Phantom(region,  self.create_inline_template(text), sublime.PhantomLayout.INLINE)

	def create_block_phantom(self, a, b, text):
		region = sublime.Region(a,b)
		return sublime.Phantom(region, self.create_inline_template(text) ,sublime.PhantomLayout.BLOCK)

	def create_invisible_phantom(self, a, b):
		region = sublime.Region(a,b)
		return sublime.Phantom(region, self.invisibleDiv, sublime.PhantomLayout.BLOCK)

	def show_start_line_completion(self, position, text):
		if len(text) <= 0 or text.isspace():
			return

		previous_line = get_previous_line(self.view, position)
		previous_line_text = self.view.substr(previous_line)

		popup_point = previous_line.a
		if previous_line_text[0] == '\t':
			popup_point = previous_line.a
			text = " " + text
		elif len(previous_line) > 0:
			popup_point = popup_point + 1

		popup_text = self.create_annotation_template(text)
		self.view.show_popup(popup_text, location = popup_point, flags = sublime.PopupFlags.HIDE_ON_CHARACTER_EVENT | sublime.HIDE_ON_MOUSE_MOVE, max_width = 999)

	def add_phantoms(self, new_phantoms):
		view = self.view
		cursor_position = view.sel()[0]

		self.phantomSet.update([])
		self.phantomSet.update(new_phantoms)
		if get_cursor_point(view) != cursor_position.b:
			set_cursor_position(view, cursor_position)

	def get_seed_completion_text(self, seed):
		cursor_point = get_cursor_point(self.view)
		line_text = get_line(self.view, cursor_point)
		rc = self.view.rowcol(cursor_point)
		completion_text = get_completion_text(cursor_point, seed.get_cursor_text(), line_text[:rc[1]], rc[1])
		return completion_text

	def add_space(self, popup_type):
		if self.added_space:
			self.remove_space()
		self.added_space = AddedSpace(self.view, popup_type)

	def remove_space(self):
		if self.added_space is None:
			return
		current_space = self.added_space
		self.added_space = None
		current_space.remove_space(self.view)

	def get_update_meta(self, seed):
		view = self.view
		cursor_point = get_cursor_point(view)
		line = view.line(cursor_point)

		if not seed.is_cursor_on_line(view, line):
			self.clear_phantoms()
			return None

		completion_text = self.get_seed_completion_text(seed)
		popup_type = line.a == cursor_point
		if completion_text and (not popup_type or line.a > 0):
			return [completion_text, popup_type]
		else:
			return None

	def handle_space(self, popup_type):
		view = self.view
		if self.added_space and not self.added_space.on_same_line(view, popup_type):
			self.remove_space()
		
		needed_space = False
		if popup_type:
			needed_space = len(get_previous_line(view, get_cursor_point(view))) <= 0
		else:
			needed_space = view.size() <= get_cursor_point(view)
		if needed_space:
			self.add_space(popup_type)

	def create_phantoms(self, seed, completion_text, popup_type):
		cursor_point = get_cursor_point(self.view)

		step_phantoms =[]
		next_inline_phantom = seed.next_inline_phantom
		next_line_phantom = seed.next_line_phantom
		if not completion_text.isspace():
			if popup_type:
				self.show_start_line_completion(cursor_point, completion_text)
			else:
				step_phantoms.append(self.create_inline_phantom(cursor_point, cursor_point + 1, completion_text))
				if not next_line_phantom:
					step_phantoms.append(self.create_invisible_phantom(cursor_point, cursor_point))

		if next_line_phantom:
			step_phantoms.append(self.create_block_phantom(cursor_point, cursor_point, seed.next_line_phantom.text))

		if next_inline_phantom and not popup_type:
			position = cursor_point + seed.next_inline_phantom.position
			step_phantoms.append(self.create_inline_phantom(position, position + 1, seed.next_inline_phantom.text))

		return step_phantoms

	def update(self):
		self.update_step = True
		self.view.hide_popup()
		phantoms = []
		meta_data = filter_none([self.get_update_meta(seed) for seed in self.seeds])

		if meta_data and len(meta_data) > 0:
			self.phantoms_visible = True
			for seed, meta in zip(self.seeds, meta_data):
				completion_text, popup_type = meta
				self.handle_space(popup_type)
				phantoms.extend(self.create_phantoms(seed, completion_text, popup_type))
			self.add_phantoms(phantoms)
		else:
			self.clear_phantoms()
		self.update_step = False

	def create_seed(self, phantom_block):
		seed = Seed(self.view, phantom_block)
		if seed.is_empty():
			return None
		else:
			return seed

	def are_phantoms_visible(self):
		return self.phantoms_visible

	def clear_phantoms(self):
		self.phantoms_visible = False
		self.view.hide_popup()
		self.phantomSet.update([])
		self.remove_space()

	# phantom_insertions is [point, text]
	def set_new_phantoms(self, phantom_insertions):
		self.seeds = filter_none([self.create_seed(phantom_insertion) for phantom_insertion in phantom_insertions])
		self.update()
