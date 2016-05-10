"""
pyDashRF1.py - Reads the shared memory map for rFactor 1 
	as provided by rFactorSharedMemoryMap.dll
by Dan Allongo (daniel.s.allongo@gmail.com)

This is a small application that makes use of the pySRD9c interface 
to display basic telemetry and status data on the dashboard.

It uses mmap to read from a shared memory handle.

Release History:
2016-05-09: Initial release
"""

APP_NAME = 'pyDashRF1'
APP_VER = '0.9.0.0'
APP_DESC = 'Python sim racing dashboard control'
APP_AUTHOR = 'Dan Allongo (daniel.s.allongo@gmail.com)'
APP_URL = 'https://github.com/dallongo/pySRD9c'

if __name__ == '__main__':
	from traceback import format_exc
	from time import sleep, time
	from sys import exit
	from distutils.util import strtobool
	from mmap import mmap
	from os.path import getmtime
	import json
	from pyRF1 import *
	from pySRD9c import srd9c

	print "{0} v.{1}".format(APP_NAME, APP_VER)
	print APP_DESC
	print APP_AUTHOR
	print APP_URL

	with open(APP_NAME + '.log', 'a+') as lfh:
		try:
			# super basic logging func, echos to console
			def log_print(s):
				print s
				if(s[-1] != '\n'):
					s += '\n'
				lfh.write(s)
			# get and validate settings from json, write back out to disk
			def read_settings(sfn):
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
							'compare_lap':'self_best'
						},
						'lap_split':{
							'_comment':"options are 'self_previous', 'self_best', 'session_best'",
							'enabled':True,
							'compare_lap':'self_best'
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
					'neutral':{
						'_comment':"options are '0', 'n', '-', '_', ' '",
						'symbol':"n"
					},
					'speed':{
						'_comment':"options are 'mph', 'km/h'",
						'units':"mph"
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
						settings['led_blink']['enabled'] = check_option(settings['led_blink']['enabled'], 'bool', defaults['led_blink']['enabled'])
						settings['info_text']['sector_split']['enabled'] = check_option(settings['info_text']['sector_split']['enabled'], 'bool', defaults['info_text']['sector_split']['enabled'])
						settings['info_text']['lap_split']['enabled'] = check_option(settings['info_text']['lap_split']['enabled'], 'bool', defaults['info_text']['lap_split']['enabled'])
						settings['info_text']['position']['enabled'] = check_option(settings['info_text']['position']['enabled'], 'bool', defaults['info_text']['position']['enabled'])
						settings['info_text']['remaining']['enabled'] = check_option(settings['info_text']['remaining']['enabled'], 'bool', defaults['info_text']['remaining']['enabled'])
						settings['text_blink']['duration'] = check_option(settings['text_blink']['duration'], 'float', defaults['text_blink']['duration'], [0.1, 1])
						settings['led_blink']['duration'] = check_option(settings['led_blink']['duration'], 'float', defaults['led_blink']['duration'], [0.1, 1])
						settings['info_text']['duration'] = check_option(settings['info_text']['duration'], 'float', defaults['info_text']['duration'], [1, 5])
						settings['info_text']['sector_split']['compare_lap'] = check_option(settings['info_text']['sector_split']['compare_lap'], 'str', defaults['info_text']['sector_split']['compare_lap'], ['self_previous', 'self_best', 'session_best'])
						settings['info_text']['lap_split']['compare_lap'] = check_option(settings['info_text']['lap_split']['compare_lap'], 'str', defaults['info_text']['lap_split']['compare_lap'], ['self_previous', 'self_best', 'session_best'])
						settings['neutral']['symbol'] = check_option(settings['neutral']['symbol'], 'str', defaults['neutral']['symbol'], ['0', 'n', '-', '_', ' '])
						settings['speed']['units'] = check_option(settings['speed']['units'], 'str', defaults['speed']['units'], ['mph', 'km/h'])
				# write out validated settings
				with open(sfn, 'w') as f:
					json.dump(settings, f, indent=4, separators=(',',': '), sort_keys=True)
				return settings
			log_print("-"*16 + " INIT " + "-"*16)
			settings_fn = APP_NAME + '.settings.json'
			settings_mtime = 0
			settings = None
			# variables
			blink_time = {'led':0, 'text':0}
			info_text_time = 0
			compare_lap = 0
			compare_sector = 0
			current_sector = 1
			samples = {'water':[], 'oil':[], 'fuel':[], 
				'avg_water':None, 'avg_oil':None, 'avg_fuel':None,
				'warn_temp':None, 'warn_fuel':3,
				'critical_temp':None, 'critical_fuel':1, 'size':7}
			compare_fuel = 0
			lastET = {'value':0, 'update':0, 'delta':0}
			log_print("Waiting for SRD-9c...")
			dash = srd9c()
			log_print("Connected!")
			try:
				rfMapHandle = mmap(fileno=0, length=sizeof(rfShared), tagname=rfMapTag)
			except:
				log_print("Unable to open shared memory map")
				log_print(format_exc())
			if(rfMapHandle):
				log_print("Shared memory mapped!")
			else:
				log_print("Shared memory not available, exiting!")
				exit(1)
			while(True):
				sleep(0.01)
				# get settings if file has changed
				if(not settings or getmtime(settings_fn) > settings_mtime):
					log_print("Reading settings from {0}".format(settings_fn))
					settings = read_settings(settings_fn)
					settings_mtime = getmtime(settings_fn)
				# read shared memory block
				rfMapHandle.seek(0)
				smm = rfShared.from_buffer_copy(rfMapHandle)
				# used by the blink timers (all things that blink do so in unison)
				if(time() - blink_time['led'] >= settings['led_blink']['duration']*2):
					blink_time['led'] = time()
				if(time() - blink_time['text'] >= settings['text_blink']['duration']*2):
					blink_time['text'] = time()
				rpm = 0
				status = ['0']*4
				if(smm.engineMaxRPM > 0):
					rpm = smm.engineRPM/smm.engineMaxRPM
					rpm -= (1 - (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*0.13)
					rpm /= (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*0.13
					if(rpm < 0):
						rpm = 0
					# blue status LED shift light at 95% of full RPM range
					if(smm.engineRPM/smm.engineMaxRPM >= 0.95):
						status[2] = '1'
				dash.rpm['value'] = rpm
				dash.gear = dict({'-2':'-', '-1':'r', '0':settings['neutral']['symbol']}, **{str(i):str(i) for i in range(1, 8)})[str(smm.gear)]
				if(settings['speed']['units'] == 'mph'):
					dash.right = '{0}'.format(int(mps_to_mph(smm.speed)))
				elif(settings['speed']['units'] == 'km/h'):
					dash.right = '{0}'.format(int(mps_to_kph(smm.speed)))
				# session time
				if(smm.currentET != lastET['value']):
					# new session, reset tracking variables
					if(smm.currentET < lastET['value']):
						compare_lap = 0
						compare_sector = 0
						current_sector = 1
						samples = {'water':[], 'oil':[], 'fuel':[], 
							'avg_water':None, 'avg_oil':None, 'avg_fuel':None,
							'warn_temp':None, 'warn_fuel':3,
							'critical_temp':None, 'critical_fuel':1, 'size':7}
						compare_fuel = 0
					lastET['value'] = smm.currentET
					lastET['update'] = time()
				lastET['delta'] = time() - lastET['update']
				# stall timer delta while not in real time
				if(lastET['delta'] > 0.5 and lastET['value'] > 0):
					lastET['delta'] = 0.5
				# get driver data
				dd = None
				bestLapTimeSession = 0
				bestSector1Session = 0
				bestSector2Session = 0
				if(smm.numVehicles > 0):
					for d in smm.vehicle:
						if(d.isPlayer):
							dd = d
						if(d.bestLapTime > 0 and (bestLapTimeSession == 0 or d.bestLapTime < bestLapTimeSession)):
							bestLapTimeSession = d.bestLapTime
						if(d.bestSector1 > 0 and (bestSector1Session == 0 or d.bestSector1 < bestSector1Session)):
							bestSector1Session = d.bestSector1
						if(d.bestSector2 > 0 and (bestSector2Session == 0 or d.bestSector2 < bestSector2Session)):
							bestSector2Session = d.bestSector2
				if(dd):
					if(smm.currentET > 0 and smm.lapStartET > 0 and smm.lapNumber > 0):
						currentLapTime = (smm.currentET + lastET['delta']) - smm.lapStartET
					else:
						currentLapTime = 0
					# no running clock on invalid/out laps
					if(currentLapTime > 0):
						dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(currentLapTime, 60))
					else:
						dash.left = '-.--.-'
					# info text timer starts upon entering each sector
					if(current_sector != dd.sector):
						info_text_time = time()
						current_sector = dd.sector
						# calculate fuel use average continuously (dimishes over time) and ignore first sector after refuel
						if(compare_fuel > 0 and compare_fuel > smm.fuel):
							samples['fuel'].append(compare_fuel - smm.fuel)
							if(len(samples['fuel']) > samples['size']):
								samples['fuel'] = samples['fuel'][-samples['size']:]
								samples['avg_fuel'] = sum(samples['fuel'])*3/len(samples['fuel'])
						compare_fuel = smm.fuel
						# calculate temps for first few laps as baseline
						if(len(samples['water']) < samples['size']):
							samples['water'].append(smm.engineWaterTemp)
						elif(not samples['avg_water']):
							samples['avg_water'] = sum(samples['water'][1:])/len(samples['water'][1:])
							samples['warn_temp'] = max(samples['water']) - min(samples['water'])
							samples['critical_temp'] = samples['warn_temp']*1.5
						if(len(samples['oil']) < samples['size']):
							samples['oil'].append(smm.engineOilTemp)
						elif(not samples['avg_oil']):
							samples['avg_oil'] = sum(samples['oil'][1:])/len(samples['oil'][1:])
					if(current_sector == 1):
						# show lap time compared to last/best/session best lap
						et = time() - info_text_time
						et_min = 0
						et_max = int(settings['info_text']['lap_split']['enabled'])*settings['info_text']['duration']
						if(et >= et_min and et < et_max and settings['info_text']['lap_split']['enabled']):
							if(dd.lastLapTime > 0):
								dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(dd.lastLapTime, 60))
							else:
								dash.left = '-.--.-'
							if(compare_lap > 0 and dd.lastLapTime > 0):
								dash.right = '{0:04.2f}'.format(dd.lastLapTime - compare_lap)
							else:
								dash.right = '--.--'
						else:
							# update comparison lap after lap display is done
							if(dd.lastLapTime > 0 and settings['info_text']['lap_split']['compare_lap'] == 'self_previous'):
								compare_lap = dd.lastLapTime
							elif(dd.bestLapTime > 0 and settings['info_text']['lap_split']['compare_lap'] == 'self_best'):
								compare_lap = dd.bestLapTime
							elif(bestLapTimeSession > 0 and settings['info_text']['lap_split']['compare_lap'] == 'session_best'):
								compare_lap = bestLapTimeSession
							else:
								compare_lap = 0
						# show position and number of cars in field
						et_min += int(settings['info_text']['lap_split']['enabled'])*settings['info_text']['duration']
						et_max += int(settings['info_text']['position']['enabled'])*settings['info_text']['duration']
						if(et >= et_min and et < et_max and settings['info_text']['position']['enabled']):
							dash.left = 'P{0}'.format(str(dd.place).rjust(3))
							dash.right = ' {0}'.format(str(smm.numVehicles).ljust(3))
						# show completed laps and laps/time remaining
						et_min += int(settings['info_text']['position']['enabled'])*settings['info_text']['duration']
						et_max += int(settings['info_text']['remaining']['enabled'])*settings['info_text']['duration']
						if(et >= et_min and et < et_max and settings['info_text']['remaining']['enabled']):
							dash.left = 'L{0}'.format(str(dd.totalLaps).rjust(3))
							if(smm.maxLaps > 0 and smm.maxLaps < 200):
								dash.right = ' {0}'.format(str(smm.maxLaps).ljust(3))
							elif(smm.endET > 0):
								dash.right = '{0:02.0f}.{1:04.1f}'.format(*divmod(smm.endET - (smm.currentET + lastET['delta']), 60))
							else:
								dash.right = ' '*4
					elif(current_sector in [2, 0] and settings['info_text']['sector_split']['enabled'] and time() - info_text_time <= settings['info_text']['duration']):
						# show sectors 1 and 2 splits
						if(dd.lastSector1 > 0 and dd.lastSector2 > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_previous'):
							compare_sector = dd.lastSector1
							if(current_sector == 0):
								compare_sector = dd.lastSector2 - dd.lastSector1
						elif(dd.bestSector1 > 0 and dd.bestSector2 > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_best'):
							compare_sector = dd.bestSector1
							if(current_sector == 0):
								compare_sector = dd.bestSector2 - dd.bestSector1
						elif(bestSector1Session > 0 and bestSector2Session > 0 and settings['info_text']['sector_split']['compare_lap'] == 'session_best'):
							compare_sector = bestSector1Session
							if(current_sector == 0):
								compare_sector = bestSector2Session - bestSector1Session
						else:
							compare_sector = 0
						if(compare_sector > 0 and currentLapTime > 0):
							sector_delta = dd.curSector1 - compare_sector
							if(current_sector == 0):
								sector_delta = (dd.curSector2 - dd.curSector1) - compare_sector
							dash.right = '{0:04.2f}'.format(sector_delta)
						else:
							dash.right = '--.--'
					# blink red status LED at critical fuel level
					if(samples['avg_fuel'] > 0 and smm.fuel/samples['avg_fuel'] <= samples['warn_fuel']):
						status[0] = '1'
						if(smm.fuel/samples['avg_fuel'] < samples['critical_fuel']):
							if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
								status[0] = '0'
							else:
								status[0] = '1'
							if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
								dash.left = 'fuel'
					# blink yellow status LED at critical oil/coolant temp
					if((samples['avg_water'] and smm.engineWaterTemp - samples['avg_water'] >= samples['warn_temp']) or
						(samples['avg_oil'] and smm.engineOilTemp - samples['avg_oil'] >= samples['warn_temp']) or smm.overheating):
						status[1] = '1'
						if((smm.engineWaterTemp - samples['avg_water'] > samples['critical_temp']) or
							(smm.engineOilTemp - samples['avg_oil'] > samples['critical_temp']) or smm.overheating):
							if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
								status[1] = '0'
							else:
								status[1] = '1'
							if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
								dash.left = 'heat'
					# blink green status LED while in pit/limiter active
					if(smm.yellowFlagState == rfYellowFlagState.pitOpen or rfYellowFlagState.pitOpen in smm.sectorFlag):
						status[3] = '1'
					if(dd.inPits):
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							status[3] = '0'
						else:
							status[3] = '1'
						if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.right = 'pit '
				# make sure engine is running
				if(smm.engineRPM > 1):
					dash.status = ''.join(status)
					dash.update()
				else:
					dash.reset()
			# never gets here				
			log_print("Closing shared memory map...")
			rfMapHandle.close()
		except:
			log_print("Unhandled exception!")
			log_print(format_exc())
