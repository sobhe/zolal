
import re
from collections import defaultdict
from pyquery import PyQuery as pq
from nltk import stem
from quran import simple_aya


isri = stem.ISRIStemmer()


def read_tafsir(tafsir):
	html = refine_html(tafsir.read())
	d = pq(html)

	for section in d.children().children().items():
		if not len(section.text().strip()):
			continue

		yield section


def section_ayas(id, ayas):
	html = ''
	sura, aya = id.split('_')
	tokens, stems = {}, {}

	for a in range(int(aya.split('-')[0]), int(aya.split('-')[1])+1):
		aya = '%s_%d' % (sura, a)
		text = ayas[aya]['raw']
		html += '<span class="aya" rel="%s">%s «%d»</span> ' % (aya, text, a)
		tokens[aya] = text.split(' ')
		stems[aya] = list(map(isri.stem, tokens[aya]))

	return html, tokens, stems


def resolve_footnotes(section):
	for footnote in section.find('.footnote:not([title])').items():
		content = section.find('.footnote-content[rel="%s"]' % footnote.attr('rel'))
		if content:
			content = pq(content[0])
			footnote.attr('title', content.html())
			content.remove()

	for footnote in section.find('.footnote-content').items():
		for rel in re.split(' +', re.sub(r'[^ \d]', ' ', footnote.attr('rel'))):
			ref = section.find('.footnote:not([title])[rel="%s"]' % rel)
			if ref:
				pq(ref[0]).attr('title', footnote.html())
			# todo check ambigous multiple footnotes
			# todo fix unresolved footnotes

		footnote.remove()

	# refine footnotes
	for footnote in section.find('.footnote').items():
		title = footnote.attr('title')
		if title:
			footnote.attr('title', refine_note(title))
		else:
			footnote.remove()


number_map = str.maketrans('1234567890', '۱۲۳۴۵۶۷۸۹۰')

def refine_numbers(text):
	return text.translate(number_map)


def refine_html(html):

	expressions = [

		# spaces
		(r'[\n ]+', r' '),

		# headers
		(r'<h3> ?\(([^\(\)]+)\) ?</h3>', r'<h3>\1</h3>'),

		# footnotes
		(r' ?: ?\n?</span>', r'</span>:'),
		(r': ?\(([^{\d\na-zA-Z]{1,10}): ?(\d+)\)', r'<span class="footnote" title="\1، \2">*</span>'),
		(r':([^{\d\na-zA-Z]{1,10})[ :،-]([0-9، ]*\d)', r'<span class="footnote" title="\1، \2">*</span>'),

		# punctuations
		(r'،? ?`', r'،'),
		(r'\*(?!</span>)', r''),
		(r'"([^"\na-z0-9<>.]{1,15})"', r' <em>\1</em> '),
		(r'([^=a-z\d])"([^=a-z\d>])', r'\1 \2'),
		(r'([\.،؛\):؟])(?=[^ :\.\d،؛\)])', r'\1 '),
		(r' ([:\)])', r'\1'),
		(r'(?=[^ ])([\(])', r' \1'),

		# fix spaces
		(r'</span>(?=[^ ،؛.\)؟])', '</span> '),
		(r'([^ \(])<span', r'\1 <span'),
		(r'</em>(?=[^ ،؛.\)؟])', '</em> '),
		(r'([^ \(])<em', r'\1 <em'),
		(r' +<span class="footnote"', '<span class="footnote"'),
		(r'‌<', '<'),
	]

	for key, value in expressions:
		html = re.sub(key, value, html)

	return html


def refine_note(text):
	result = text
	if result.startswith('-'):
		result = result[1:]
	return refine_numbers(result.strip())


def refine_translation(section):
	for trans in section.find('.trans').items():
		html = trans.html()
		html = re.sub(r'[ -]*\(\d+\) *', '', str(html))

		# add aya number
		aya = trans.attr('rel').split('_')[1]
		if int(aya):
			html = html + ' «%s»' % refine_numbers(aya)
		trans.html(html + ' ')


def refine_section(section):

	# ayas
	for item in section.find('.aya').items():
		text = simple_aya(item.text())
		if text.startswith('(') and text.startswith('('):
			text = text[1:-1]
		item.text(text)

	# structure
	refine_translation(section)
	for item in section.children().items():
		if item[0].tag == 'p':
			if len(item.text().strip()) <= 1:
				item.remove()
			else:
				if len(item.find('.trans')) >= 1:
					for span in section.find('.trans').items():
						item.append(span.outerHtml())
						span.remove()


def resolve_phrases(section, tokens, stems, book, id):

	# find and resolve parantheses
	if book == 'almizan_fa':
		if int(id.split('_')[0]) <= 2:
			html = section.html()
			replace = lambda start, end, oldtext, newtext: oldtext[:start] + newtext + oldtext[end:]

			# in chapter1, remove parantheses for ayas
			iter = re.finditer(r'(<span[^\n]*>)[ ]*\(([^\)s]*)\)[^\)]*(</span[^\n]*>)', html)
			for m in reversed(list(iter)):
				html = replace(m.start(), m.end(), html, m.group().replace('(','').replace(')',''))

			iter = re.finditer(r'\([^\)]{3,15}\)', html)
			for match in reversed(list(iter)):
				m = match.group()[1:-1]
				rel = resolve_phrase(m, tokens, stems, book[-2:])
				if rel:
					html = replace(match.start(), match.end(), html, '<em rel="{0}">{1}</em>'.format(rel, m))

			section.html(html)

	# resolve em elements
	for em in section.find('em').items():
		rel = resolve_phrase(em.text(), tokens, stems, book[-2:])
		if rel:
			em.attr('rel', rel)


def resolve_phrase(text, tokens, stems, book):
	rel = None
	text  = text.strip().replace('ة','ه').replace('ؤ','و')
	if len(text) < 3:
		return None

	#resolve aya tokens with or without Alif-Lam
	for aya, token_list in tokens.items():
		for t, token in enumerate(token_list):
			if text == token or (token[:2] == 'ال' and text == token[2:]) or (token[:1] in 'لبکف' and text == token[1:]):
				return '{0}_{1}_{2}-{2}'.format(book, aya, t+1)

	#resolve aya stems
	text = isri.stem(text.replace('‌', ''))
	for aya, stem_list in stems.items():
		for s, stm in enumerate(stem_list):
			if text == stm:
				rel = '{0}_{1}_{2}-{2}'.format(book, aya, s+1)
				break

	return rel
