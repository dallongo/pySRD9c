"""
pyDashR3E.py - Reads the shared memory map for RaceRoom Racing Experience 
	as outlined by Sector3 Studios (https://github.com/sector3studios/r3e-api)
by Dan Allongo (daniel.s.allongo@gmail.com)

This is a small application that makes use of the pySRD9c interface 
to display basic telemetry and status data on the dashboard.

It uses mmap to read from a shared memory handle.

Release History:
2016-05-31: Fix array index type error (float instead of int) for fuel array slicing
2016-05-30: Weighted moving average used for fuel estimates and temperature averages
2016-05-29: Information messages printed to log
2016-05-28: Improved session detection
2016-05-27: RPM range and shift lights now configurable via settings
	Fuel and temperature warnings can now be tuned/disabled via settings
2016-05-26: Integrate with pyDash
2016-05-12: Fix DRS LEDs for DTM 2013-2016 classes
2016-05-09: Add missing sanity check for 'drs_ptp' settings
	Fix errors in fuel and sector split calculations (again)
2016-05-07: Merge DRS with PTP LED routine
	Added version number to start up console output
	Updated temp/fuel logic (average first 2 laps as baseline)
2016-05-06: Added settings.json (re-reads file on change while running)
	Split off shared memory structure definitions to separate file
	Fixed sector split calculations
2016-05-05: Added sector split times
	All split times now compared to previous lap, properly handle invalid laps
	Fixed race session time/laps remaining
	Added very basic logging
	Fixed position and session time/laps remaining not showing when current lap invalidated within first few seconds
	Consolidated sector split time and lap time information display
	Basic code clean-up and comments added
	Removed psutil dependency
2016-05-04: Updated per https://github.com/mrbelowski/CrewChiefV4/blob/master/CrewChiefV4/R3E/RaceRoomData.cs
	Added blinking effect for critical warnings and DRS/PTP/pit events
	Added lap/split display
2016-05-04: Initial release
"""

from traceback import format_exc
from time import sleep, time
from mmap import mmap
from os.path import getmtime
from pyR3E import *
from psutil import pid_exists

def pyDashR3E(pid, log_print, read_settings, dash):
	try:
		log_print("-"*16 + " R3E INIT " + "-"*16)
		settings, settings_fn = read_settings()
		settings_mtime = getmtime(settings_fn)
		# variables
		blink_time = {'led':0, 'text':0}
		compare_lap = 0
		compare_sector = 0
		info_text_time = 0
		current_sector = 0
		samples = {'water':[], 'oil':[], 'fuel':[], 
			'avg_water':None, 'avg_oil':None, 'avg_fuel':None}
		compare_fuel = 0
		current_session = []
		print_info = True
		try:
			r3e_smm_handle = mmap(fileno=0, length=sizeof(r3e_shared), tagname=r3e_smm_tag)
		except:
			log_print("Unable to open shared memory map")
			log_print(format_exc())
		if(r3e_smm_handle):
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
			r3e_smm_handle.seek(0)
			smm = r3e_shared.from_buffer_copy(r3e_smm_handle)
			# get driver data
			dd = None
			if(smm.num_cars > 0):
				if([smm.session_type, smm.track_info.track_id, smm.track_info.layout_id] == current_session):
					for d in smm.all_drivers_data_1:
						if(d.driver_info.slot_id == smm.slot_id):
							dd = d
							break
				else:
					log_print("New session detected!")
					# clear session variables on exiting session
					compare_lap = 0
					compare_sector = 0
					info_text_time = 0
					current_sector = 0
					samples = {'water':[], 'oil':[], 'fuel':[], 
						'avg_water':None, 'avg_oil':None, 'avg_fuel':None}
					compare_fuel = 0
					current_session = [smm.session_type, smm.track_info.track_id, smm.track_info.layout_id]
					print_info = True
			else:
				current_session = []
			if(dd):
				# use green RPM LEDs for PTP when available
				if((smm.push_to_pass.amount_left > 0 or smm.push_to_pass.engaged > -1 or smm.drs_engaged > 0 or 
					# DTM 2013, 2014, 2015, 2016
					(smm.drs_available == 1 and dd.driver_info.class_id in [1921, 3086, 4260, 5262])) and settings['drs_ptp']['led']):
					dash.rpm['use_green'] = False
				elif((smm.push_to_pass.available < 1 and smm.push_to_pass.engaged < 1) or (smm.drs_engaged == 0 and smm.drs_available == 0) or not settings['drs_ptp']['led']):
					dash.rpm['use_green'] = True
				# used by the blink timers (all things that blink do so in unison)
				if(time() - blink_time['led'] >= settings['led_blink']['duration']*2):
					blink_time['led'] = time()
				if(time() - blink_time['text'] >= settings['text_blink']['duration']*2):
					blink_time['text'] = time()
				rpm = 0
				status = ['0']*4
				if(smm.max_engine_rps > 0):
					rpm = smm.engine_rps/smm.max_engine_rps
					rpm -= (1 - (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*settings['rpm']['range'])
					rpm /= (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*settings['rpm']['range']
					if(rpm < 0):
						rpm = 0
					# blue status LED shift light at 95% of full RPM range
					if(smm.engine_rps/smm.max_engine_rps >= settings['rpm']['shift']):
						status[2] = '1'
				dash.rpm['value'] = rpm
				dash.gear = dict({'-2':'-', '-1':'r', '0':settings['neutral']['symbol']}, **{str(i):str(i) for i in range(1, 8)})[str(smm.gear)]
				if(settings['speed']['units'] == 'mph'):
					dash.right = '{0}'.format(int(mps_to_mph(smm.car_speed)))
				elif(settings['speed']['units'] == 'km/h'):
					dash.right = '{0}'.format(int(mps_to_kph(smm.car_speed)))
				# no running clock on invalid/out laps
				if(smm.lap_time_current_self > 0):
					dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(smm.lap_time_current_self, 60))
				else:
					dash.left = '-.--.-'
				# info text timer starts upon entering each sector
				if(current_sector != dd.track_sector):
					info_text_time = time()
					current_sector = dd.track_sector
					print_info = True
					# calculate fuel use average continuously (dimishes over time) and ignore first sector after refuel
					if(settings['fuel']['enabled'] and smm.fuel_use_active == 1):
						if(compare_fuel > 0 and compare_fuel > smm.fuel_left):
							samples['fuel'].append(compare_fuel - smm.fuel_left)
							if(len(samples['fuel']) > 3*settings['fuel']['samples']):
								samples['fuel'] = samples['fuel'][int(-3*settings['fuel']['samples']):]
								wn = 0
								wd = 0
								for i in xrange(0,len(samples['fuel'])):
									wn += samples['fuel'][i]*(i+1)
									wd += (i+1)
								samples['avg_fuel'] = wn*3/wd
								log_print("Average fuel use: {0:4.2f} L per lap".format(samples['avg_fuel']))
						compare_fuel = smm.fuel_left
					# calculate temps for first few laps as baseline
					if(settings['temperature']['enabled']):
						if(len(samples['water']) < 3*settings['temperature']['samples']):
							samples['water'].append(smm.engine_water_temp)
						elif(not samples['avg_water']):
							wn = 0
							wd = 0
							for i in xrange(0,len(samples['water'])):
								wn += samples['water'][i]*(i+1)
								wd += (i+1)
							samples['avg_water'] = wn/wd
							log_print("Average water temperature: {0:4.2f} C".format(samples['avg_water']))
						if(len(samples['oil']) < 3*settings['temperature']['samples']):
							samples['oil'].append(smm.engine_oil_temp)
						elif(not samples['avg_oil']):
							wn = 0
							wd = 0
							for i in xrange(0,len(samples['oil'])):
								wn += samples['oil'][i]*(i+1)
								wd += (i+1)
							samples['avg_oil'] = wn/wd
							log_print("Average oil temperature: {0:4.2f} C".format(samples['avg_oil']))
				if(current_sector == 1):
					# show lap time compared to last/best/session best lap
					et = time() - info_text_time
					et_min = 0
					et_max = int(settings['info_text']['lap_split']['enabled'])*settings['info_text']['duration']
					if(et >= et_min and et < et_max and settings['info_text']['lap_split']['enabled']):
						if(smm.lap_time_previous_self > 0):
							dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(smm.lap_time_previous_self, 60))
						else:
							dash.left = '-.--.-'
						if(compare_lap > 0 and smm.lap_time_previous_self > 0):
							dash.right = '{0:04.2f}'.format(smm.lap_time_previous_self - compare_lap)
						else:
							dash.right = '--.--'
						if(print_info):
							log_print("Lap time (split): {0} ({1})".format(dash.left, dash.right))
							print_info = False
					else:
						# update comparison lap after lap display is done
						if(smm.lap_time_previous_self > 0 and settings['info_text']['lap_split']['compare_lap'] == 'self_previous'):
							compare_lap = smm.lap_time_previous_self
						elif(smm.lap_time_best_self > 0 and settings['info_text']['lap_split']['compare_lap'] == 'self_best'):
							compare_lap = smm.lap_time_best_self
						elif(smm.lap_time_best_leader > 0 and settings['info_text']['lap_split']['compare_lap'] == 'session_best'):
							compare_lap = smm.lap_time_best_leader
						else:
							compare_lap = 0
					# show position and number of cars in field
					et_min += int(settings['info_text']['lap_split']['enabled'])*settings['info_text']['duration']
					et_max += int(settings['info_text']['position']['enabled'])*settings['info_text']['duration']
					if(et >= et_min and et < et_max and settings['info_text']['position']['enabled']):
						dash.left = 'P{0}'.format(str(smm.position).rjust(3))
						dash.right = ' {0}'.format(str(smm.num_cars).ljust(3))
					# show completed laps and laps/time remaining
					et_min += int(settings['info_text']['position']['enabled'])*settings['info_text']['duration']
					et_max += int(settings['info_text']['remaining']['enabled'])*settings['info_text']['duration']
					if(et >= et_min and et < et_max and settings['info_text']['remaining']['enabled']):
						dash.left = 'L{0}'.format(str(smm.completed_laps).rjust(3))
						if(smm.number_of_laps > 0):
							dash.right = ' {0}'.format(str(smm.number_of_laps).ljust(3))
						elif(smm.session_time_remaining > 0):
							dash.right = '{0:02.0f}.{1:04.1f}'.format(*divmod(smm.session_time_remaining, 60))
						else:
							dash.right = ' '*4
				elif(current_sector in [2, 3] and settings['info_text']['sector_split']['enabled'] and time() - info_text_time <= settings['info_text']['duration']):
					# show sectors 1 and 2 splits
					if(smm.lap_time_previous_self > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_previous'):
						compare_sector = dd.sector_time_previous_self[current_sector - 2]
						if(current_sector == 3):
							compare_sector -= dd.sector_time_previous_self[0]
					elif(dd.sector_time_best_self[current_sector - 2] > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_best'):
						compare_sector = dd.sector_time_best_self[current_sector - 2]
						if(current_sector == 3):
							compare_sector -= dd.sector_time_best_self[0]
					elif(smm.session_best_lap_sector_times[current_sector - 2] > 0 and settings['info_text']['sector_split']['compare_lap'] == 'session_best'):
						compare_sector = smm.session_best_lap_sector_times[current_sector - 2]
						if(current_sector == 3):
							compare_sector -= smm.session_best_lap_sector_times[0]
					else:
						compare_sector = 0
					if(compare_sector > 0 and smm.lap_time_current_self > 0):
						sector_delta = dd.sector_time_current_self[current_sector - 2] - compare_sector
						if(current_sector == 3):
							sector_delta -= dd.sector_time_current_self[0]
						dash.right = '{0:04.2f}'.format(sector_delta)
					else:
						dash.right = '--.--'
				# blink red status LED at critical fuel level
				if(settings['fuel']['enabled'] and samples['avg_fuel'] and smm.fuel_left/samples['avg_fuel'] <= settings['fuel']['warning']):
					status[0] = '1'
					if(smm.fuel_left/samples['avg_fuel'] < settings['fuel']['critical']):
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							status[0] = '0'
						else:
							status[0] = '1'
						if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = 'fuel'
				# blink yellow status LED at critical oil/coolant temp
				if(settings['temperature']['enabled'] and ((samples['avg_water'] and smm.engine_water_temp - samples['avg_water'] >= settings['temperature']['warning']) or
					(samples['avg_oil'] and smm.engine_oil_temp - samples['avg_oil'] >= settings['temperature']['warning']))):
					status[1] = '1'
					if((smm.engine_water_temp - samples['avg_water'] > settings['temperature']['critical']) or
						(smm.engine_oil_temp - samples['avg_oil'] > settings['temperature']['critical'])):
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							status[1] = '0'
						else:
							status[1] = '1'
						if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = 'heat'
				# blink green status LED while in pit/limiter active
				if(smm.pit_window_status == r3e_pit_window.R3E_PIT_WINDOW_OPEN):
					status[3] = '1'
				if(smm.pit_window_status == r3e_pit_window.R3E_PIT_WINDOW_STOPPED or smm.pit_limiter == 1):
					if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
						status[3] = '0'
					else:
						status[3] = '1'
					if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
						dash.right = 'pit '
				# blink green RPM LED during PTP cool-down, charging effect on last 4 seconds
				if(not dash.rpm['use_green']):
					if(smm.push_to_pass.wait_time_left >= 0 and smm.push_to_pass.wait_time_left <= 4):
						dash.rpm['green'] = ('0'*(int(smm.push_to_pass.wait_time_left))).rjust(4, '1')
					else:
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							dash.rpm['green'] = '0100'
						else:
							dash.rpm['green'] = '1000'
				# blink green RPM LED during DRS/PTP engaged, depleting effect on last 4 seconds
				# blink PTP activations remaining on display while PTP engaged
				if(smm.push_to_pass.engaged == 1 or smm.drs_engaged == 1):
					if(smm.push_to_pass.engaged_time_left >= 0 and smm.push_to_pass.engaged_time_left <= 4):
						dash.rpm['green'] = ('1'*(int(smm.push_to_pass.engaged_time_left))).rjust(4, '0')
					else:
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							dash.rpm['green'] = '0110'
						else:
							dash.rpm['green'] = '1001'
						if(settings['drs_ptp']['text'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = ' ptp'
							dash.right = str(smm.push_to_pass.amount_left).ljust(4)
							if(smm.drs_engaged == 1):
								dash.left = 'drs '
								dash.right = ' on '
			# make sure engine is running
			if(dd and rps_to_rpm(smm.engine_rps) > 1):
				dash.status = ''.join(status)
				dash.update()
			else:
				dash.reset()
	except:
		log_print("Unhandled exception!")
		log_print(format_exc())
	finally:
		log_print("Closing shared memory map...")
		r3e_smm_handle.close()
		log_print("-"*16 + " R3E SHUTDOWN " + "-"*16)
