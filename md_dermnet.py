#!/usr/bin/python
# -*- coding: utf-8 -*-
__NOTICE__ = '''
md_dermnet.py

Task:
Upload to wdwiki from DermNet NZ
Categories need a second run for creation, trying to avoid empty categories

Date
	2021 February Create

Author: Fæ
Permissions: CC-BY-SA-4.0

Example:
python pwb.py md_dermnet
'''
import requests, os
import pywikibot, upload, sys, urllib2, urllib, re, string, time
from pywikibot import pagegenerators
from BeautifulSoup import BeautifulSoup
from sys import argv
from time import sleep
from colorama import Fore, Back, Style
from colorama import init
init()

site = pywikibot.getSite('en', 'mdwiki')

def up(source, pagetitle, desc, comment, iw):
	if source[:4] == 'http':
		source_url=source; source_filename=None
		# Resolve url redirects to find end target (the API will not do this)
		headers = { 'User-Agent' : 'Mozilla/5.0' }
		req = urllib2.Request(source_url, None, headers)
		res = urllib2.urlopen(req)
		source_url = res.geturl()
	else:
		source_url=None; source_filename=source

	if iw:
		site.upload(pywikibot.FilePage(site, 'File:' + pagetitle),
			source_filename=source_filename,
			source_url=source_url,
			comment=comment,
			text=desc,
			ignore_warnings = True,
			chunk_size= 400000,#1048576,
			#async = True,
			)
	else:
		site.upload(pywikibot.FilePage(site, 'File:' + pagetitle),
			source_filename=source_filename,
			source_url=source_url,
			comment=comment,
			text=desc,
			ignore_warnings = False,
			chunk_size = 400000,#1048576,
			#async = True,
			)

def uptry(source, filename, desc, comment, iw):
		countErr=0
		r=True
		while r:
				try:
						up(source, filename, desc, comment, iw)
						return ''
				except Exception as e:						
						countErr+=1
						try:
							ecode = e.code
						except Exception as ee:
							ecode = str(e)
						if re.search("ratelimited", str(e)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							wait = min(60*countErr, 300)
							print Fore.GREEN, "Sleeping for {}s".format(wait), Fore.WHITE
							sleep(wait)
							if countErr>3:
								countErr = 3
								print Fore.MAGENTA, "Consider increasing ratelimit lag of", ratelimit, Fore.WHITE
						if re.search("multiple", str(e)):
							print Fore.MAGENTA, ecode, Fore.WHITE
						if re.search("429", str(ecode)):
							# Too many requests
							wait = min(30*countErr, 300)
							print Fore.MAGENTA, "Too many requests" + Fore.GREEN,
							if wait>90:
								print Fore.RED,
							print "Wait {}s".format(wait),
							if wait>30:
								cumwait = countErr * (countErr + 1.) * 15.
								print "(total {:.3g}m)".format(cumwait/60.),
							print Fore.WHITE
							sleep(wait)
							continue
						if re.search('File exists with different extension', str(ecode)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							return ''
						if re.search('The uploaded file contains errors', str(ecode)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							return ''
						if re.search('exists-normalized', str(ecode)):
							#print Fore.MAGENTA, ecode, Fore.WHITE
							iw = True
							continue
						if re.search("was-deleted", str(e)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							print Fore.RED, "Already deleted, skipping", Fore.WHITE
							return ''
						if re.search('fileexists-shared-forbidden', str(ecode)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							return ''
						if re.search('fileexists-no-change', str(ecode)):
							print Fore.MAGENTA, ecode, Fore.WHITE
							return ''
						if re.search('exists', str(ecode)):
							if countErr>10:
								print Fore.RED, countErr, "tries made, skipping", Fore.WHITE
								return ''
							if countErr>1:
								print Fore.MAGENTA, countErr, ecode, Fore.WHITE
							iw = True
							continue
						if re.search("image/png", str(e)):
							return "png"
						if re.search("image/tiff", str(e)):
							return "tiff"
						if re.search("verification-error", str(e)):
							print Fore.RED, "Verification error, bad format", Fore.WHITE
							return ''
						if re.search("script code", str(e)):
							print Fore.RED, "Looks like a bad file format", Fore.WHITE
							return ''
						if re.search("copyuploadbaddomain", str(e)):
							print Fore.RED, "Bad domain for url upload", Fore.WHITE
							sleep(60)
							return ''
						if countErr>4: return
						print Fore.RED, str(e), Fore.WHITE
						if re.search("duplicate|nochange", str(e).lower()):
							return ''
						print Fore.MAGENTA, ecode, Fore.WHITE
						#print Fore.CYAN,'** ERROR Upload failed', Fore.WHITE
						time.sleep(1)
		return ''

subs = [
	['\t|\n', ' '],
	[' > ', ' more than '],
	[' < ', ' less than '],
	[u'\uFFFD', '?'],
	[u'Ì', 'I'],
	[u'ï', 'i'],
	[u'¸', ''],
	[u'¡', 'i'],
	[u'\x8c', '?'],
	[u"", 'Œ'],
	[u"Ã", u'Ü'], [u"Ã¤", u'ä'],
	[u'Ã¼', u'ü'], [u"u", u'ü'],
	[u'eÌ', u'é'],
	['&lt;|&gt;|\|\\\\', '-'],
	['\x5c|\|', '-'],
	[r'[:\/\<\>]+','-'],
	['&quot;|&#39;', "'"],
	['#|--','-'],
	["'{2,}", "'"], # titleblacklist-custom-double-apostrophe
	[' {2,}', ' '],
	['[\[\{]','('],
	['[\]\}]', ')'],
	['&amp;', '&'],
	['& ?c[\.;,]', 'etc.'],
	['\uFFFD', '~'],
	]

def dosubs(st):
	for s in subs:
		st = re.sub(s[0],s[1], st)
	return st

print Fore.CYAN+"*"*70
print __NOTICE__
print Fore.GREEN+"*"*70
DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'TEMP')

domain = 'https://dermnetnz.org'
topurl = domain + '/topics/'
#"https://creativecommons.org/licenses/by-nc-nd/3.0/nz/"
# downloads should be limited to 'Watermarked'

req = requests.get(topurl)
html = req.text
gsoup = BeautifulSoup(html)
topics = gsoup.findAll('a', href=re.compile(".*/topics/.*"))
topiclist = set()
catthtml = "[[Category:Skin topics]]"
count = 0
print len(topics)
for a in topics:
	turl = a['href']
	if len(turl)<10: continue
	turl = domain + turl
	print Fore.GREEN, turl
	try:
		tsoup = BeautifulSoup(requests.get(turl).text)
	except Exception as e:
		print Fore.MAGENTA, str(e), Fore.WHITE
		continue
	try:
		topic = tsoup.find('h1').text
	except:
		continue
	details = tsoup.findAll('a', href=re.compile("^imagedetail.*"))
	if len(details)==0:
		continue
	if not topic in topiclist:
		topiclist.add(topic)
		catt = pywikibot.Category(site, u'Category:' + topic)
		lencatt = len([a for a in catt.articles()])
		if lencatt !=0:
			print Fore.CYAN, topic, "({})".format(lencatt), Fore.WHITE
			if not catt.exists():
				pywikibot.setAction('Create category from DermNet topic')
				catt.put(catthtml)
	for i in details:
		desc = u"" + i.findNext('p').text
		durl = domain + '/' + i['href']
		dsoup = BeautifulSoup(requests.get(durl).text)
		source = domain + dsoup.find('img', src = re.compile("^/assets/Uploads.*"))['src']
		fn = dosubs(source.split('Uploads/')[1].split('__')[0])
		filename = u"{} (DermNet NZ {}).jpg".format(dosubs(desc), fn)
		if len(filename)>200:
			filename = "DermNet NZ {}.jpg".format(fn)
		p = pywikibot.Page(site, 'File:' + filename)
		if p.exists():
			print Fore.RED, filename, "exists", Fore.WHITE
			continue
		count += 1
		dd = "== Summary =="
		# information template not yet implemented
		'''dd += "\n{{information"
		dd += "\n|description = " + desc 
		dd += "\n|source = [" + durl + " dermnetnz.org]"
		dd += "\n* Gallery page: " + turl
		dd += "\n|author = DermNet New Zealand"
		dd += "\n|date = 2021-02-20"
		dd += "\n}}\n"'''
		#
		dd += "\n:Description: " + desc
		dd += "\n:Source: [" + durl + " dermnetnz.org]"
		dd += "\n:Gallery page: " + turl
		dd += "\n:Author: DermNet New Zealand"
		dd += "\n:Date: 2021-02-18"
		dd += "\n\n== License ==\n"
		dd += "{{Cc-by-nc-nd-3.0-nz}}\n\n"
		dd += "\n[[Category:" + topic + "|" + fn + u"]]\n[[Category:DermNet images|" + fn + u"]]\n[[Category:Uploads by Fæ]]"
		comment = u"[[User:Fæ/DermNet|DermNet]] " + fn
		local = DIR + '/dermnet.jpg'
		print Fore.CYAN, count, Fore.GREEN + source, Fore.WHITE
		req = requests.get(source, allow_redirects=True)
		open(local, 'wb').write(req.content)
		#urllib.urlretrieve(source, local)
		uptry(local, filename, dd, comment, False)
