"""
pyDashR3E.py - Reads the shared memory map for RaceRoom Racing Experience 
	as outlined by Sector3 Studios (https://github.com/sector3studios/r3e-api)
by Dan Allongo (daniel.s.allongo@gmail.com)

This is a small application that makes use of the pySRD9c interface 
to display basic telemetry and status data on the dashboard.

It uses mmap to read from a shared memory handle.

Release History:
2016-05-06: Added settings.json (re-reads file on change while running)
	Split off shared memory structure definitions to separate file
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
2016-05-04: Inital release
"""

if __name__ == '__main__':
	from traceback import format_exc
	from time import sleep, time
	from sys import exit
	from distutils.util import strtobool
	from mmap import mmap
	from os.path import getmtime
	import json
	from pyR3E import *
	from pySRD9c import srd9c

	with open('pyDashR3E.log', 'a+') as lfh:
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
							'compare_lap':'self_previous'
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
						'_comment':"text and green RPM LEDs for DRS/PTP",
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
					}
				}
				# get settings from json
				with open(sfn, 'a+') as f:
					try:
						# merge with defaults to catch missing keys
						settings = dict(defaults, **json.load(f))
					except ValueError:
						log_print("Invalid settings JSON, using defaults")
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
			settings_fn = 'pyDashR3E.settings.json'
			settings_mtime = 0
			settings = None
			# variables
			blink_time = {'led':0, 'text':0}
			compare_lap = 0
			compare_sector = 0
			info_text_time = 0
			current_sector = 0
			log_print("Waiting for SRD-9c...")
			dash = srd9c()
			log_print("Connected!")
			log_print("Waiting for shared memory map...")
			try:
				r3e_smm_handle = mmap(fileno=0, length=sizeof(r3e_shared), tagname=r3e_smm_tag)
			except:
				log_print("Unable to open shared memory map")
				log_print(format_exc())
			if(r3e_smm_handle):
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
				r3e_smm_handle.seek(0)
				smm = r3e_shared.from_buffer_copy(r3e_smm_handle)
				# use green RPM LEDs for PTP when available
				if((smm.push_to_pass.amount_left > 0 or smm.push_to_pass.engaged > 0 or smm.drs_engaged > 0) and settings['drs_ptp']['led']):
					dash.rpm['use_green'] = False
				elif(smm.push_to_pass.available < 1 and smm.push_to_pass.engaged < 1 and smm.drs_engaged < 1):
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
					rpm -= (1 - (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*0.13)
					rpm /= (int(dash.rpm['use_green']) + int(dash.rpm['use_red']) + int(dash.rpm['use_blue']))*0.13
					if(rpm < 0):
						rpm = 0
					# blue status LED shift light at 95% of full RPM range
					if(smm.engine_rps/smm.max_engine_rps >= 0.95):
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
				# get driver data
				dd = None
				if(smm.num_cars > 0):
					for d in smm.all_drivers_data_1:
						if(d.driver_info.slot_id == smm.slot_id):
							dd = d
							break
				if(dd):
					# info text timer starts upon entering each sector
					if(current_sector != dd.track_sector):
						info_text_time = time()
						current_sector = dd.track_sector
					if(current_sector == 1):
						# show lap time compared to last/best/session best lap
						et = time() - info_text_time
						et_min = 0
						et_max = int(settings['info_text']['lap_split']['enabled'])*settings['info_text']['duration']
						if(et > et_min and et <= et_max and settings['info_text']['lap_split']['enabled']):
							if(smm.lap_time_previous_self > 0):
								dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(smm.lap_time_previous_self, 60))
							else:
								dash.left = '-.--.-'
							if(compare_lap > 0 and smm.lap_time_previous_self > 0):
								dash.right = '{0:04.2f}'.format(smm.lap_time_previous_self - compare_lap)
							else:
								dash.right = '--.--'
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
						if(et > et_min and et <= et_max and settings['info_text']['position']['enabled']):
							dash.left = 'P{0}'.format(str(smm.position).rjust(3))
							dash.right = ' {0}'.format(str(smm.num_cars).ljust(3))
						# show completed laps and laps/time remaining
						et_min += int(settings['info_text']['position']['enabled'])*settings['info_text']['duration']
						et_max += int(settings['info_text']['remaining']['enabled'])*settings['info_text']['duration']
						if(et > et_min and et <= et_max and settings['info_text']['remaining']['enabled']):
							dash.left = 'L{0}'.format(str(smm.completed_laps).rjust(3))
							if(smm.number_of_laps > 0):
								dash.right = ' {0}'.format(str(smm.number_of_laps).ljust(3))
							elif(smm.session_time_remaining > 0):
								dash.right = '{0:02.0f}.{1:04.1f}'.format(*divmod(smm.session_time_remaining, 60))
							else:
								dash.right = ' '*4
					elif(current_sector in [2, 3] and settings['info_text']['sector_split']['enabled'] and time() - info_text_time <= settings['info_text']['duration']):
						# show sectors 1 and 2 splits
						if(dd.sector_time_previous_self[current_sector - 2] > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_previous'):
							compare_sector = dd.sector_time_previous_self[current_sector - 2]
						if(dd.sector_time_best_self[current_sector - 2] > 0 and settings['info_text']['sector_split']['compare_lap'] == 'self_best'):
							compare_sector = dd.sector_time_best_self[current_sector - 2]
						if(smm.session_best_lap_sector_times[current_sector - 2] > 0 and settings['info_text']['sector_split']['compare_lap'] == 'session_best'):
							compare_sector = smm.session_best_lap_sector_times[current_sector - 2]
						else:
							compare_sector = 0
						if(compare_sector > 0 and dd.sector_time_current_self[current_sector - 2] > 0):
							dash.right = '{0:04.2f}'.format(dd.sector_time_current_self[current_sector - 2] - compare_sector)
						else:
							dash.right = '--.--'
				# blink red status LED at critical fuel level
				if(smm.fuel_use_active == 1 and smm.fuel_capacity > 0 and smm.fuel_left/smm.fuel_capacity <= 0.1):
					status[0] = '1'
					if(smm.fuel_left/smm.fuel_capacity < 0.05):
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							status[0] = '0'
						else:
							status[0] = '1'
						if(settings['text_blink']['enabled'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = 'fuel'
				# blink yellow status LED at critical coolant temp
				if(smm.engine_water_temp >= 91):
					status[1] = '1'
					if(smm.engine_water_temp > 93):
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
				# blink green RPM LED and DRS on display while DRS engaged (untested)
				if(smm.drs_engaged == 1):
					if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
						dash.rpm['green'] = '0110'
					else:
						dash.rpm['green'] = '1001'
					if(settings['drs_ptp']['text'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
						dash.left = 'drs '
						dash.right = ' on '
				# blink green RPM LED during PTP cool-down, charging effect on last 4 seconds
				if(smm.push_to_pass.amount_left > 0):
					if(smm.push_to_pass.wait_time_left <= 4):
						dash.rpm['green'] = ('0'*(int(smm.push_to_pass.wait_time_left))).rjust(4, '1')
					else:
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							dash.rpm['green'] = '0000'
						else:
							dash.rpm['green'] = '1000'
				# blink green RPM LED during PTP engaged, depleting effect on last 4 seconds
				# blink PTP activations remaining on display while PTP engaged
				if(smm.push_to_pass.engaged == 1):
					if(smm.push_to_pass.engaged_time_left <= 4):
						dash.rpm['green'] = ('1'*(int(smm.push_to_pass.engaged_time_left))).rjust(4, '0')
					else:
						if(settings['led_blink']['enabled'] and time() - blink_time['led'] <= settings['led_blink']['duration']):
							dash.rpm['green'] = '0110'
						else:
							dash.rpm['green'] = '1001'
						if(settings['drs_ptp']['text'] and time() - blink_time['text'] <= settings['text_blink']['duration']):
							dash.left = ' ptp'
							dash.right = str(smm.push_to_pass.amount_left).ljust(4)
				dash.status = ''.join(status)
				# make sure engine is running
				if(smm.engine_rps > 0):
					dash.update()
				else:
					dash.reset()
				
			log_print("Closing shared memory map...")
			r3e_smm_handle.close()
		except:
			log_print("Unhandled exception!")
			log_print(format_exc())
