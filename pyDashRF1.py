"""
pyDashRF1.py - Reads the shared memory map for rFactor 1 
	as provided by rFactorSharedMemoryMap.dll
by Dan Allongo (daniel.s.allongo@gmail.com)

This is a small application that makes use of the pySRD9c interface 
to display basic telemetry and status data on the dashboard.

It uses mmap to read from a shared memory handle.

Release History:
2016-05-30: Weighted moving average used for fuel estimates
2016-05-29: Information messages printed to log
2016-05-28: Improved session detection
2016-05-27: RPM range and shift lights now configurable via settings
	Fuel and temperature warnings can now be tuned/disabled via settings
2016-05-26: Integrate with pyDash
2016-05-09: Initial release
"""

from traceback import format_exc
from time import sleep, time
from mmap import mmap
from os.path import getmtime
from pyRF1 import *
from psutil import pid_exists

def pyDashRF1(pid, log_print, read_settings, dash):
	try:
		log_print("-"*16 + " RF1 INIT " + "-"*16)
		settings, settings_fn = read_settings()
		settings_mtime = getmtime(settings_fn)
		# variables
		blink_time = {'led':0, 'text':0}
		info_text_time = 0
		compare_lap = 0
		compare_sector = 0
		current_sector = 1
		samples = {'fuel':[], 'avg_fuel':None}
		compare_fuel = 0
		current_session = []
		print_info = True
		try:
			rfMapHandle = mmap(fileno=0, length=sizeof(rfShared), tagname=rfMapTag)
		except:
			log_print("Unable to open shared memory map")
			log_print(format_exc())
		if(rfMapHandle):
			log_print("Shared memory mapped!")
		else:
			log_print("Shared memory not available, exiting!")
			return
		while(pid_exists(pid)):
			sleep(0.01)
			# get settings if file has changed
			if(not settings or getmtime(settings_fn) > settings_mtime):
				log_print("Reading settings from {0}".format(settings_fn))
				settings = read_settings()[0]
				settings_mtime = getmtime(settings_fn)
			# read shared memory block
			rfMapHandle.seek(0)
			smm = rfShared.from_buffer_copy(rfMapHandle)
			# get driver data
			dd = None
			bestLapTimeSession = 0
			bestSector1Session = 0
			bestSector2Session = 0
			if(smm.numVehicles > 0):
				if([smm.session, smm.trackName, smm.vehicleName] == current_session):
					for d in smm.vehicle:
						if(d.isPlayer):
							dd = d
						if(d.bestLapTime > 0 and (bestLapTimeSession == 0 or d.bestLapTime < bestLapTimeSession)):
							bestLapTimeSession = d.bestLapTime
						if(d.bestSector1 > 0 and (bestSector1Session == 0 or d.bestSector1 < bestSector1Session)):
							bestSector1Session = d.bestSector1
						if(d.bestSector2 > 0 and (bestSector2Session == 0 or d.bestSector2 < bestSector2Session)):
							bestSector2Session = d.bestSector2
				else:
					log_print("New session detected!")
					# clear session variables on exiting session
					compare_lap = 0
					compare_sector = 0
					info_text_time = 0
					current_sector = 1
					samples = {'fuel':[], 'avg_fuel':None}
					compare_fuel = 0
					current_session = [smm.session, smm.trackName, smm.vehicleName]
					print_info = True
			else:
				current_session = []
			if(dd):
				# used by the blink timers (all things that blink do so in unison)
				if(time() - blink_time['led'] >= settings['led_blink']['duration']*2):
					blink_time['led'] = time()
				if(time() - blink_time['text'] >= settings['text_blink']['duration']*2):
					blink_time['text'] = time()
				rpm = 0
				status = ['0']*4
				if(smm.engineMaxRPM > 0):
					rpm = smm.engineRPM/smm.engineMaxRPM
					rpm -= (1 - (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*settings['rpm']['range'])
					rpm /= (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*settings['rpm']['range']
					if(rpm < 0):
						rpm = 0
					# blue status LED shift light at 95% of full RPM range
					if(smm.engineRPM/smm.engineMaxRPM >= settings['rpm']['shift']):
						status[2] = '1'
				dash.rpm['value'] = rpm
				dash.gear = dict({'-2':'-', '-1':'r', '0':settings['neutral']['symbol']}, **{str(i):str(i) for i in range(1, 8)})[str(smm.gear)]
				if(settings['speed']['units'] == 'mph'):
					dash.right = '{0}'.format(int(mps_to_mph(smm.speed)))
				elif(settings['speed']['units'] == 'km/h'):
					dash.right = '{0}'.format(int(mps_to_kph(smm.speed)))
				if(smm.currentET > 0 and smm.lapStartET > 0 and smm.lapNumber > 0):
					currentLapTime = smm.currentET - smm.lapStartET
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
					print_info = True
					# calculate fuel use average continuously (dimishes over time) and ignore first sector after refuel
					if(settings['fuel']['enabled'] and compare_fuel > 0 and compare_fuel > smm.fuel):
						samples['fuel'].append(compare_fuel - smm.fuel)
						if(len(samples['fuel']) > 3*settings['fuel']['samples']):
							samples['fuel'] = samples['fuel'][-3*settings['fuel']['samples']:]
							wn = 0
							wd = 0
							for i in xrange(0,len(samples['fuel'])):
								wn += samples['fuel'][i]*(i+1)
								wd += (i+1)
							samples['avg_fuel'] = wn*3/wd
							log_print("Average fuel use: {0:4.2f} L per lap".format(samples['avg_fuel']))
					compare_fuel = smm.fuel
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
						if(print_info):
							log_print("Lap time (split): {0} ({1})".format(dash.left, dash.right))
							print_info = False
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
							dash.right = '{0:02.0f}.{1:04.1f}'.format(*divmod(smm.endET - smm.currentET, 60))
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
				if(settings['fuel']['enabled'] and samples['avg_fuel'] > 0 and smm.fuel/samples['avg_fuel'] <= settings['fuel']['warning']):
					status[0] = '1'
					if(smm.fuel/samples['avg_fuel'] < settings['fuel']['critical']):
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							status[0] = '0'
						else:
							status[0] = '1'
						if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = 'fuel'
				# blink yellow status LED at critical oil/coolant temp
				if(settings['temperature']['enabled'] and smm.overheating):
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
			if(dd and smm.engineRPM > 1):
				dash.status = ''.join(status)
				dash.update()
			else:
				dash.reset()
	except:
		log_print("Unhandled exception!")
		log_print(format_exc())
	finally:
		log_print("Closing shared memory map...")
		rfMapHandle.close()
		log_print("-"*16 + " RF1 SHUTDOWN " + "-"*16)
