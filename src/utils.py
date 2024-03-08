import sublime
import sublime_plugin

def get_cursor_point(view):
	return view.sel()[0].b

def get_text(view):
	return view.substr(sublime.Region(0, view.size()))

def get_cursor_line(view):
	return get_line(view, get_cursor_point(view))

def get_line(view, point):
	line = view.line(point)
	return view.substr(line)

def get_previous_line(view, point):
	line = view.line(point)
	return view.line(line.a - 1)

def set_cursor_position(view, position):
	sel = view.sel()
	if len(sel) > 0 and sel[0].intersects(position):
		return
	view.sel().clear()
	view.sel().add(position)

def is_position_end_of_line(view, position):
	rc = view.rowcol(position)
	text = get_line(view, position)
	print("is_position_end_of_line rc", rc, "text ", text, " len", len(text))
	return rc[1] >= len(text)

def filter_none(l):
	return list(filter(identity, l))

def identity(x):
	return x

def get_tab_size():
	s = sublime.load_settings("Preferences.sublime-settings")
	return s.get("tab_size", 4)

def replace_tab(text, tab_size = None):
	if tab_size is None:
		tab_size = get_tab_size()
	return text.replace('\t', ' ' * tab_size)


