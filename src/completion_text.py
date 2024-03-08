from .utils import *

def get_nonwhitespace(s, start = 0):
	end = len(s)
	for i in range(start, end):
		if not s[i].isspace():
			return i
	return end

def is_name_char(c):
	return c.isdigit() or c.isalpha() or c == '_'

def resolve_space_diff(a, b, a_index, b_index):
	a_char = a[a_index]
	b_char = b[b_index]
	if a_char != b_char:
		if a_char.isspace() and b_index > 0 and is_name_char(b[b_index - 1]):
			return False
		if b_char.isspace() and a_index > 0 and is_name_char(a[a_index - 1]):
			return False
	return True

def find_diff(a, b):
	a_index = get_nonwhitespace(a, 0)
	b_index = get_nonwhitespace(b, 0)
	while a_index < len(a) and b_index < len(b):
		a_char = a[a_index]
		b_char = b[b_index]
		if ((a_char.isspace() or b_char.isspace() ) and not resolve_space_diff(a, b, a_index, b_index)):
			break
		a_index = get_nonwhitespace(a, a_index)
		b_index = get_nonwhitespace(b, b_index)
		if a_index >= len(a) or b_index >= len(b) or a[a_index] != b[b_index]:
			break
		a_index = a_index + 1
		b_index = b_index + 1
	return [a_index, b_index]

def collect_space(s, index):
	space = ""
	while index >= 0 and index < len(s) and s[index].isspace():
		space = s[index] + space
		index = index - 1
	return space

def get_completion_text(point, text, line, end = None):
	if not line or line.isspace():
		tab_size = get_tab_size()

		s = replace_tab(text, tab_size)
		res_space = get_nonwhitespace(s)
		line_len = len(replace_tab(line, tab_size))
		if res_space > line_len:
			return s[line_len:]
		else:
			return s[res_space:]

	diff = find_diff(text, line)
	end = end or len(line)

	if diff[1] < end:
		return None
	else:
		if diff[0] > 0 and text[diff[0] - 1].isspace():
			text_space = collect_space(text, diff[0] - 1)
			line_index = diff[1] if diff[1] < len(line) and line[diff[1]].isspace() else diff[1] - 1
			line_space = collect_space(line, line_index)
			if len(text_space) > len(line_space):
				size_diff = len(text_space) - len(line_space)
				remain_space = text_space[(len(text_space) - size_diff):]
				return remain_space + text[diff[0]:]
		return text[diff[0]:]
