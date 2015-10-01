#!/usr/bin/env python

import time
import subprocess
import select
import resource
import re
import os
import sys
import syslog

LOGFILE = "/var/log/sixad"
SYSLOG = True


# Daemonize

try:
	pid = os.fork()
	if pid > 0:
		sys.exit(0)
except OSError, e:
	print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
	sys.exit(1)

os.chdir('/')
os.setsid()
os.umask(0)

try:
	pid = os.fork()
	if pid > 0:
		print "Sixad restart daemon running on pid %d" % pid
		sys.exit(0)
except OSError, e:
	print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
	sys.exit(1)

maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
if (maxfd == resource.RLIM_INFINITY):
	maxfd = 1024

for fd in range(0, maxfd):
	try:
		os.close(fd)
	except OSError:
		pass

os.open("/dev/null", os.O_RDWR)
os.dup2(0, 1)
os.dup2(0, 2)


# Main

syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

f = subprocess.Popen(['tail', '-F', LOGFILE], stdout=subprocess.PIPE,stderr=subprocess.PIPE)
p = select.poll()
p.register(f.stdout)

# clear buffer so we only monitor from the end of the file
if p.poll(1):
	data = f.stdout.read()

try:
	while True:
		if p.poll(1):
			line = f.stdout.readline()
			match1 = re.match(r'^.*Bad Sixaxis buffer \(out of battery\?\), disconneting now\.\.\.$', line)
			if match1:
				syslog.syslog(syslog.LOG_INFO, "disconnect detected")

			match2 = re.match(r'^.*Sixaxis was not in use, and timeout reached, disconneting\.\.\.$', line)
			if match2:
				syslog.syslog(syslog.LOG_INFO, "timeout detected")

			if match1 or match2:
				if os.fork() == 0:
					os.setsid()
					if os.fork() == 0:
						syslog.syslog(syslog.LOG_INFO, "restarting sixad daemon")
						subprocess.call(['service', 'sixad', 'restart'])
						subprocess.call(['service', 'sixad', 'restart'])
						subprocess.call(['service', 'sixad', 'restart'])
						sys.exit(0)
		time.sleep(1)
except:
	sys.exit(0)


