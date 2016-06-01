"""
pyDash.py - Waits for sim to launch and then starts appropriate Dash app
by Dan Allongo (daniel.s.allongo@gmail.com)

Release History:
2016-05-30: Add multiple instance detection
2016-05-29: Add timestamp to each log message
2016-05-28: Clear display after exiting sim
2016-05-27: Add settings for fuel, temperature, and RPM range to unified settings JSON
2016-05-26: Initial release
"""

APP_NAME = 'pyDash'
APP_VER = '2.0.0.1'
APP_DESC = 'Python sim racing dashboard control'
APP_AUTHOR = 'Dan Allongo (daniel.s.allongo@gmail.com)'
APP_URL = 'https://github.com/dallongo/pySRD9c'

if __name__ == '__main__':
	from pyDashR3E import pyDashR3E
	from pyDashRF1 import pyDashRF1
	from pySRD9c import srd9c

	from time import sleep
	from psutil import process_iter, Process
	from sys import exit
	from distutils.util import strtobool
	import json
	from datetime import datetime

	print "{0} v.{1}".format(APP_NAME, APP_VER)
	print APP_DESC
	print APP_AUTHOR
	print APP_URL

	# only one instance running at a time to avoid race condition
	pid = None
	for p in process_iter():
		# compiled exe with pyinstaller runs as child process during unpacking
		if(p.pid in [Process().pid, Process().ppid()]):
			continue
		try:
			if(p.cmdline() == Process().cmdline()):
				pid = p.pid
				break
		except:
			pass
	if(pid):
		print "\nERROR: Instance in PID {0} already running, exiting!".format(pid)
		sleep(3)
		exit(1)
	# super basic logging func, echos to console
	def log_print(s, lfn=APP_NAME + '.log'):
		with open(lfn, 'a+') as lfh:
			# append timestamp to start of each log message
			s = '\t'.join([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), s])
			print s
			if(not s or s[-1] != '\n'):
				s += '\n'
			lfh.write(s)
	# get and validate settings from json, write back out to disk
	def read_settings(sfn=APP_NAME + '.settings.json'):
		# verify options are valid
		def check_option(option, val_type='float', default=0, val_range=[0, 1]):
			x = None
			try:
				if(val_type=='float'):
					x = float(str(option))
					if(x < min(val_range) or x > max(val_range)):
						raise ValueError
				elif(val_type=='bool'):
					x = bool(strtobool(str(option)))
				elif(val_type=='str'):
					x = str(option)
					if(x not in val_range):
						raise ValueError
			except ValueError:
				log_print("Bad option value {0}, using default value {1}".format(option, default))
				return default
			return x
		# default settings
		defaults = {
			'text_blink':{
				'_comment':"blink text for pit/overheat/fuel warnings. values 0.1-1.0",
				'enabled':True,
				'duration':0.5
			},
			'led_blink':{
				'_comment':"blink indicators for DRS/PTP/pit/overheat/fuel warnings. values 0.1-1.0",
				'enabled':True,
				'duration':0.2
			},
			'info_text':{
				'sector_split':{
					'_comment':"options are 'self_previous', 'self_best', 'session_best'",
					'enabled':True,
					'compare_lap':'session_best'
				},
				'lap_split':{
					'_comment':"options are 'self_previous', 'self_best', 'session_best'",
					'enabled':True,
					'compare_lap':'self_previous'
				},
				'position':{
					'_comment':"show position in field at the beginning of each lap",
					'enabled':True
				},
				'remaining':{
					'_comment':"show laps/time remaining at the beginning of each lap",
					'enabled':True
				},
				'_comment':"session timing info for each sector/lap. values 1.0-5.0",
				'duration':3
			},
			'drs_ptp':{
				'_comment':"(R3E only) text and green RPM LEDs for DRS/PTP",
				'text':True,
				'led':True
			},
			'neutral':{
				'_comment':"options are '0', 'n', '-', '_', ' '",
				'symbol':"n"
			},
			'speed':{
				'_comment':"options are 'mph', 'km/h'",
				'units':"mph"
			},
			'fuel':{
				'_comment':"tune fuel warnings. 'samples' is how many laps to use for the moving average of fuel use (values 1.0-5.0). 'warning' is how many laps of fuel left to turn on LED (values 2.0-5.0). 'critical' is how many laps of fuel left to blink LED (values 0.5-2.0).",
				'warning':3,
				'critical':1,
				'samples':3,
				'enabled':True
			},
			'temperature':{
				'_comment':"tune temperature warnings. 'samples' is how many laps to use for the initial baseline (values 1.0-5.0). 'warning' is how many degrees C above baseline to turn on LED (values 2.0-10.0). 'critical' is how many degrees C above baseline to blink LED (values 10.0-20.0).",
				'warning':7,
				'critical':12,
				'samples':3,
				'enabled':True
			},
			'rpm':{
				'_comment':"change tach/shift points. 'range' is what fraction of the RPM range is represented by each group of 4 LEDs (values 0.05-0.33). 'shift' is what fraction of the RPM range to trigger the shift LED (values 0.85-1.0).",
				'range':0.13,
				'shift':0.95
			}
		}
		# get settings from json
		with open(sfn, 'a+') as f:
			try:
				# merge with defaults to catch missing keys
				settings = dict(defaults, **json.load(f))
			except ValueError:
				log_print("Invalid or missing settings file, creating using defaults")
				settings = defaults
			if(settings != defaults):
				# validate setting values
				settings['text_blink']['enabled'] = check_option(settings['text_blink']['enabled'], 'bool', defaults['text_blink']['enabled'])
				settings['text_blink']['duration'] = check_option(settings['text_blink']['duration'], 'float', defaults['text_blink']['duration'], [0.1, 1])

				settings['led_blink']['enabled'] = check_option(settings['led_blink']['enabled'], 'bool', defaults['led_blink']['enabled'])
				settings['led_blink']['duration'] = check_option(settings['led_blink']['duration'], 'float', defaults['led_blink']['duration'], [0.1, 1])

				settings['info_text']['sector_split']['enabled'] = check_option(settings['info_text']['sector_split']['enabled'], 'bool', defaults['info_text']['sector_split']['enabled'])
				settings['info_text']['sector_split']['compare_lap'] = check_option(settings['info_text']['sector_split']['compare_lap'], 'str', defaults['info_text']['sector_split']['compare_lap'], ['self_previous', 'self_best', 'session_best'])
				settings['info_text']['lap_split']['enabled'] = check_option(settings['info_text']['lap_split']['enabled'], 'bool', defaults['info_text']['lap_split']['enabled'])
				settings['info_text']['lap_split']['compare_lap'] = check_option(settings['info_text']['lap_split']['compare_lap'], 'str', defaults['info_text']['lap_split']['compare_lap'], ['self_previous', 'self_best', 'session_best'])
				settings['info_text']['position']['enabled'] = check_option(settings['info_text']['position']['enabled'], 'bool', defaults['info_text']['position']['enabled'])
				settings['info_text']['remaining']['enabled'] = check_option(settings['info_text']['remaining']['enabled'], 'bool', defaults['info_text']['remaining']['enabled'])
				settings['info_text']['duration'] = check_option(settings['info_text']['duration'], 'float', defaults['info_text']['duration'], [1, 5])

				settings['neutral']['symbol'] = check_option(settings['neutral']['symbol'], 'str', defaults['neutral']['symbol'], ['0', 'n', '-', '_', ' '])
				settings['speed']['units'] = check_option(settings['speed']['units'], 'str', defaults['speed']['units'], ['mph', 'km/h'])

				settings['drs_ptp']['text'] = check_option(settings['drs_ptp']['text'], 'bool', defaults['drs_ptp']['text'])
				settings['drs_ptp']['led'] = check_option(settings['drs_ptp']['led'], 'bool', defaults['drs_ptp']['led'])

				settings['fuel']['enabled'] = check_option(settings['fuel']['enabled'], 'bool', defaults['fuel']['enabled'])
				settings['fuel']['samples'] = check_option(settings['fuel']['samples'], 'float', defaults['fuel']['samples'], [1, 5])
				settings['fuel']['warning'] = check_option(settings['fuel']['warning'], 'float', defaults['fuel']['warning'], [2, 5])
				settings['fuel']['critical'] = check_option(settings['fuel']['critical'], 'float', defaults['fuel']['critical'], [0.5, 2])

				settings['temperature']['enabled'] = check_option(settings['temperature']['enabled'], 'bool', defaults['temperature']['enabled'])
				settings['temperature']['samples'] = check_option(settings['temperature']['samples'], 'float', defaults['temperature']['samples'], [1, 5])
				settings['temperature']['warning'] = check_option(settings['temperature']['warning'], 'float', defaults['temperature']['warning'], [2, 10])
				settings['temperature']['critical'] = check_option(settings['temperature']['critical'], 'float', defaults['temperature']['critical'], [10, 20])

				settings['rpm']['range'] = check_option(settings['rpm']['range'], 'float', defaults['rpm']['range'], [0.05, 0.33])
				settings['rpm']['shift'] = check_option(settings['rpm']['shift'], 'float', defaults['rpm']['shift'], [0.85, 1.0])
		# write out validated settings
		with open(sfn, 'w') as f:
			json.dump(settings, f, indent=4, separators=(',',': '), sort_keys=True)
		return settings, sfn
	log_print("-"*16 + " pyDash INIT " + "-"*16)
	settings, settings_fn = read_settings()
	log_print("Waiting for SRD-9c...")
	dash = srd9c()
	log_print("Connected!")
	while(True):
		sleep(1)
		try:
			for p in process_iter():
				if(p.name().lower() in ['rrre.exe', 'gsc.exe', 'ams.exe', 'rfactor.exe']):
					log_print("Found {0}".format(p.name()))
					if(p.name().lower() == 'rrre.exe'):
						pyDashR3E(p.pid, log_print, read_settings, dash)
					else:
						pyDashRF1(p.pid, log_print, read_settings, dash)
					# clear display after exiting sim
					dash.gear = ' '
					dash.left = ' '*4
					dash.right = ' '*4
					dash.rpm['value'] = 0
					dash.rpm['green'] = '0'*4
					dash.rpm['red'] = '0'*4
					dash.rpm['blue'] = '0'*4
					dash.status = '0'*4
					dash.update()
					break
		except:
			log_print("Unhandled exception!")
			log_print(format_exc())
	log_print("-"*16 + " pyDash SHUTDOWN " + "-"*16)
