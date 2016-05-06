"""
r3e.py - Reads the shared memory map for RaceRoom Racing Experience 
	as outlined by Sector3 Studios (https://github.com/sector3studios/r3e-api)
by Dan Allongo (daniel.s.allongo@gmail.com)

This is a small application that makes use of the pySRD9c interface 
to display basic telemetry and status data on the dashboard.

It uses mmap to read from a shared memory handle.

Release History:
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

from ctypes import *
from mmap import mmap

class r3e_struct(Structure):
	_pack_ = 1

class r3e_session_enum(r3e_struct):
	_fields_ = [('R3E_SESSION_UNAVAILABLE', c_int),
				('R3E_SESSION_PRACTICE', c_int),
				('R3E_SESSION_QUALIFY', c_int),
				('R3E_SESSION_RACE', c_int)]
r3e_session = r3e_session_enum(-1, 0, 1, 2)

class r3e_session_phase_enum(r3e_struct):
	_fields_ = [('R3E_SESSION_PHASE_UNAVAILABLE', c_int),
				('R3E_SESSION_PHASE_GARAGE', c_int),
				('R3E_SESSION_PHASE_GRIDWALK', c_int),
				('R3E_SESSION_PHASE_FORMATION', c_int),
				('R3E_SESSION_PHASE_COUNTDOWN', c_int),
				('R3E_SESSION_PHASE_GREEN', c_int),
				('R3E_SESSION_PHASE_CHECKERED', c_int),
				('R3E_SESSION_PHASE_TERMINATED', c_int)]
r3e_session_phase = r3e_session_phase_enum(-1, 0, 2, 3, 4, 5, 6, 7)

class r3e_control_enum(r3e_struct):
	_fields_ = [('R3E_CONTROL_UNAVAILABLE', c_int),
				('R3E_CONTROL_PLAYER', c_int),
				('R3E_CONTROL_AI', c_int),
				('R3E_CONTROL_REMOTE', c_int),
				('R3E_CONTROL_REPLAY', c_int)]
r3e_control = r3e_control_enum(-1, 0, 1, 2, 3)

class r3e_pit_window_enum(r3e_struct):
	_fields_ = [('R3E_PIT_WINDOW_UNAVAILABLE', c_int),
				('R3E_PIT_WINDOW_DISABLED', c_int),
				('R3E_PIT_WINDOW_CLOSED', c_int),
				('R3E_PIT_WINDOW_OPEN', c_int),
				('R3E_PIT_WINDOW_STOPPED', c_int),
				('R3E_PIT_WINDOW_COMPLETED', c_int)]
r3e_pit_window = r3e_pit_window_enum(-1, 0, 1, 2, 3, 4)

class r3e_tire_type_enum(r3e_struct):
	_fields_ = [('R3E_TIRE_TYPE_UNAVAILABLE', c_int),
				('R3E_TIRE_TYPE_OPTION', c_int),
				('R3E_TIRE_TYPE_PRIME', c_int)]
r3e_tire_type = r3e_tire_type_enum(-1, 0, 1)

class r3e_pitstop_status_enum(r3e_struct):
	_fields_ = [('R3E_PITSTOP_STATUS_UNAVAILABLE', c_int),
				('R3E_PITSTOP_STATUS_UNSERVED', c_int),
				('R3E_PITSTOP_STATUS_SERVED', c_int)]
r3e_pitstop_status = r3e_pitstop_status_enum(-1, 0, 1)

class r3e_finish_status_enum(r3e_struct):
	_fields_ = [('R3E_FINISH_STATUS_UNAVAILABLE', c_int),
				('R3E_FINISH_STATUS_NONE', c_int),
				('R3E_FINISH_STATUS_FINISHED', c_int),
				('R3E_FINISH_STATUS_DNF', c_int),		# did not finish
				('R3E_FINISH_STATUS_DNQ', c_int),		# did not qualify
				('R3E_FINISH_STATUS_DNS', c_int),		# did not start
				('R3E_FINISH_STATUS_DQ', c_int)]		# disqualified
r3e_finish_status = r3e_finish_status_enum(-1, 0, 1, 2, 3, 4, 5)

class r3e_vec3_f32(r3e_struct):
	_fields_ = [('x', c_float),
				('y', c_float),
				('z', c_float)]

class r3e_vec3_f64(r3e_struct):
	_fields_ = [('x', c_double),
				('y', c_double),
				('z', c_double)]

class r3e_ori_f32(r3e_struct):
	_fields_ = [('pitch', c_float),
				('yaw', c_float),
				('roll', c_float)]

class r3e_tire_temps(r3e_struct):
	_fields_ = [('frontleft_left', c_float),
				('frontleft_center', c_float),
				('frontleft_right', c_float),
				('frontright_left', c_float),
				('frontright_center', c_float),
				('frontright_right', c_float),
				('rearleft_left', c_float),
				('rearleft_center', c_float),
				('rearleft_right', c_float),
				('rearright_left', c_float),
				('rearright_center', c_float),
				('rearright_right', c_float)]

class r3e_playerdata(r3e_struct):
	_fields_ = [('game_simulation_ticks', c_int),	# ticks (400/s)
				('_padding1', c_int),
				('game_simulation_time', c_double),	# s
				('position', r3e_vec3_f64),
				('velocity', r3e_vec3_f64),			# m/s
				('acceleration', r3e_vec3_f64),		# m/s^2
				('local_acceleration', r3e_vec3_f64),	# m/s^2
				('orientation', r3e_vec3_f64),
				('rotation', r3e_vec3_f64),
				('angular_acceleration', r3e_vec3_f64),
				('driver_acceleration', r3e_vec3_f64)]	# m/s^2

class r3e_flags(r3e_struct):
	_fields_ = [('yellow', c_int),		# not used
				('blue', c_int),		# not used
				('black', c_int)]

class r3e_car_damage(r3e_struct):
	_fields_ = [('engine', c_float),
				('transmission', c_float),
				('aerodynamics', c_float),
				('tire_front_left', c_float),
				('tire_front_right', c_float),
				('tire_rear_left', c_float),
				('tire_rear_right', c_float)]

class r3e_tire_pressure(r3e_struct):
	_fields_ = [('front_left', c_float),
				('front_right', c_float),
				('rear_left', c_float),
				('rear_right', c_float)]

class r3e_brake_temps(r3e_struct):
	_fields_ = [('front_left', c_float),
				('front_right', c_float),
				('rear_left', c_float),
				('rear_right', c_float)]

class r3e_cut_track_penalties(r3e_struct):
	_fields_ = [('drive_through', c_int),
				('stop_and_go', c_int),
				('pit_stop', c_int),
				('time_deduction', c_int),
				('slow_down', c_int)]

class r3e_tyre_dirt(r3e_struct):
	_fields_ = [('front_left', c_float),
				('front_right', c_float),
				('rear_left', c_float),
				('rear_right', c_float)]

class r3e_wheel_speed(r3e_struct):
	_fields_ = [('front_left', c_float),
				('front_right', c_float),
				('rear_left', c_float),
				('rear_right', c_float)]

class r3e_track_info(r3e_struct):
	_fields_ = [('track_id', c_int),
				('layout_id', c_int),
				('length', c_float)]

class r3e_push_to_pass(r3e_struct):
	_fields_ = [('available', c_int),
				('engaged', c_int),
				('amount_left', c_int),
				('engaged_time_left', c_float),
				('wait_time_left', c_float)]

class r3e_driver_info(r3e_struct):
	_fields_ = [('name', c_char*64),
				('car_number', c_int),
				('class_id', c_int),
				('model_id', c_int),
				('team_id', c_int),
				('livery_id', c_int),
				('manufacturer_id', c_int),
				('slot_id', c_int),
				('class_performance_index', c_int)]

class r3e_driver_data_1(r3e_struct):
	_fields_ = [('driver_info', r3e_driver_info),
				('finish_status', c_int),
				('place', c_int),
				('lap_distance', c_float),
				('position', r3e_vec3_f32),
				('track_sector', c_int),
				('completed_laps', c_int),
				('current_lap_valid', c_int),
				('lap_time_current_self', c_float),
				('sector_time_current_self', c_float*3),
				('sector_time_previous_self', c_float*3),
				('sector_time_best_self', c_float*3),
				('time_delta_front', c_float),
				('time_delta_behind', c_float),
				('pitstop_status', c_int),
				('in_pitlane', c_int),
				('num_pitstops', c_int),
				('penalties', r3e_cut_track_penalties),
				('car_speed', c_float),
				('tire_type', c_int)]

class r3e_shared(r3e_struct):
	_fields_ = [('user_input', c_float*6),			# not used
				('engine_rps', c_float),			# rad/s
				('max_engine_rps', c_float),		# rad/s
				('fuel_pressure', c_float),			# kPa
				('fuel_left', c_float),				# L
				('fuel_capacity', c_float),			# L
				('engine_water_temp', c_float),		# C
				('engine_oil_temp', c_float),		# C
				('engine_oil_pressure', c_float),	# kPa
				('car_speed', c_float),				# m/s
				('number_of_laps', c_int),
				('completed_laps', c_int),
				('lap_time_best_self', c_float),	# s
				('lap_time_previous_self', c_float),# s
				('lap_time_current_self', c_float),	# s
				('position', c_int),
				('num_cars', c_int),
				('gear', c_int),
				('tire_temps', r3e_tire_temps),		# C
				('num_penalties', c_int),
				('car_cg_location', r3e_vec3_f32),
				('car_orientation', r3e_ori_f32),	# rad
				('local_acceleration', r3e_vec3_f32),	# m/s^2
				('drs_available', c_int),
				('drs_engaged', c_int),
				('_padding1', c_int),
				('player', r3e_playerdata),
				('event_index', c_int),
				('session_type', c_int),
				('session_phase', c_int),
				('session_iteration', c_int),
				('control_type', c_int),
				('throttle_pedal', c_float),
				('brake_pedal', c_float),
				('clutch_pedal', c_float),
				('brake_bias', c_float),			# rear bias
				('tire_pressure', r3e_tire_pressure),	# kPa
				('tire_wear_active', c_int),
				('tire_type', c_int),
				('brake_temps', r3e_brake_temps),	# C
				('fuel_use_active', c_int),
				('session_time_remaining', c_float),# s
				('lap_time_best_leader', c_float),	# s
				('lap_time_best_leader_class', c_float),	# s
				('lap_time_delta_self', c_float),	# s
				('lap_time_delta_leader', c_float),	# s
				('lap_time_delta_leader_class', c_float),	# s
				('sector_time_delta_self', c_float*3),	# s
				('sector_time_delta_leader', c_float*3),# s
				('session_best_lap_sector_times', c_float*3),# s
				('time_delta_front', c_float),		# s
				('time_delta_behind', c_float),		# s
				('pit_window_status', c_int),
				('pit_window_start', c_int),		# laps or minutes
				('pit_window_end', c_int),			# laps or minutes
				('cut_track_warnings', c_int),
				('penalties', r3e_cut_track_penalties),
				('flags', r3e_flags),
				('car_damage', r3e_car_damage),
				('slot_id', c_int),
				('tyre_dirt', r3e_tyre_dirt),
				('pit_limiter', c_int),
				('wheel_speed', r3e_wheel_speed),	# rad/s
				('track_info', r3e_track_info),
				('push_to_pass', r3e_push_to_pass),
				('all_drivers_data_1', r3e_driver_data_1*128)]

def rps_to_rpm(r):
	return (r * 9.549296596)

def mps_to_mph(m):
	return (m * 2.23694)

def kpa_to_psi(k):
	return (k * 0.145038)

def c_to_f(c):
	return (c * 1.8) + 32

def l_to_g(l):
	return (l * 0.264172)

r3e_smm_tag = '$Race$'
r3e_smm_handle = None

if __name__ == '__main__':
	from traceback import format_exc
	from time import sleep, time
	from sys import exit
	from pySRD9c import srd9c

	# super basic logging func, echos to console
	def log_print(fh, s):
		print s
		if(s[-1] != '\n'):
			s += '\n'
		fh.write(s)
	# variables
	blink_duration = 0.5
	blink_last = 0
	previous_lap = None
	sector_split_duration = 3
	sector_split_last = 0
	sector_split_sector = 0
	log_filename = 'log.txt'
	with open(log_filename, 'w') as lfh:
		try:
			log_print(lfh, "Waiting for SRD-9c...")
			dash = srd9c()
			log_print(lfh, "Connected!")
			log_print(lfh, "Waiting for shared memory map...")
			try:
				r3e_smm_handle = mmap(fileno=0, length=sizeof(r3e_shared), tagname=r3e_smm_tag)
			except:
				log_print(lfh, "Unable to open shared memory map")
				log_print(lfh, format_exc())
			if(r3e_smm_handle):
				log_print(lfh, "Shared memory mapped!")
			else:
				log_print(lfh, "Shared memory not available, exiting!")
				exit(1)
			while(True):
				sleep(0.01)
				# read shared memory block
				r3e_smm_handle.seek(0)
				smm = r3e_shared.from_buffer_copy(r3e_smm_handle)
				# use green RPM LEDs for PTP when available
				if(smm.push_to_pass.amount_left > 0 or smm.push_to_pass.engaged > 0 or smm.drs_engaged > 0):
					dash.rpm['use_green'] = False
				elif(smm.push_to_pass.available < 1 and smm.push_to_pass.engaged < 1 and smm.drs_engaged < 1):
					dash.rpm['use_green'] = True
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
				dash.gear = dict({'-2':'-', '-1':'r', '0':'n'}, **{str(i):str(i) for i in range(1, 8)})[str(smm.gear)]
				dash.right = '{0}'.format(int(mps_to_mph(smm.car_speed)))
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
					if(sector_split_sector != dd.track_sector):
						sector_split_last = time()
						sector_split_sector = dd.track_sector
					if(dd.track_sector == 1):
						# show lap/split times compared to last lap
						if(time() - sector_split_last <= sector_split_duration):
							if(smm.lap_time_previous_self > 0):
								dash.left = '{0:01.0f}.{1:04.1f}'.format(*divmod(smm.lap_time_previous_self, 60))
							else:
								dash.left = '-.--.-'
							if(previous_lap and smm.lap_time_previous_self > 0):
								dash.right = '{0:04.2f}'.format(smm.lap_time_previous_self - previous_lap)
							else:
								dash.right = '--.--'
						# show position and number of cars in field
						elif(time() - sector_split_last <= sector_split_duration*2):
							if(smm.lap_time_previous_self > 0):
								previous_lap = smm.lap_time_previous_self
							else:
								previous_lap = None
							dash.left = 'P{0}'.format(str(smm.position).rjust(3))
							dash.right = ' {0}'.format(str(smm.num_cars).ljust(3))
						# show completed laps and laps/time remaining
						elif(time() - sector_split_last <= sector_split_duration*3):
							dash.left = 'L{0}'.format(str(smm.completed_laps).rjust(3))
							if(smm.number_of_laps > 0):
								dash.right = ' {0}'.format(str(smm.number_of_laps).ljust(3))
							elif(smm.session_time_remaining > 0):
								dash.right = '{0:02.0f}.{1:04.1f}'.format(*divmod(smm.session_time_remaining, 60))
							else:
								dash.right = ' '*4
					elif(dd.track_sector in [2, 3]):
						# show sectors 1 and 2 splits
						if(time() - sector_split_last <= sector_split_duration):
							if(dd.sector_time_previous_self[dd.track_sector - 2] > 0 and dd.sector_time_current_self[dd.track_sector - 2] > 0):
								dash.right = '{0:04.2f}'.format(dd.sector_time_current_self[dd.track_sector - 2] - dd.sector_time_previous_self[dd.track_sector - 2])
							else:
								dash.right = '--.--'
				# blink red status LED at critical fuel level
				if(smm.fuel_use_active == 1 and smm.fuel_capacity > 0 and smm.fuel_left/smm.fuel_capacity <= 0.1):
					status[0] = '1'
					if(smm.fuel_left/smm.fuel_capacity < 0.05):
						if(time() - blink_last >= blink_duration*2):
							blink_last = time()
						if(time() - blink_last <= blink_duration):
							status[0] = '1'
							dash.left = 'fuel'
						if(time() - blink_last > blink_duration):
							status[0] = '0'
				# blink yellow status LED at critical coolant temp
				if(smm.engine_water_temp >= 91):
					status[1] = '1'
					if(smm.engine_water_temp > 93):
						if(time() - blink_last >= blink_duration*2):
							blink_last = time()
						if(time() - blink_last <= blink_duration):
							status[1] = '1'
						if(time() - blink_last > blink_duration):
							status[1] = '0'
							dash.left = 'heat'
				# blink green status LED while in pit/limiter active
				if(smm.pit_window_status == r3e_pit_window.R3E_PIT_WINDOW_OPEN):
					status[3] = '1'
				if(smm.pit_window_status == r3e_pit_window.R3E_PIT_WINDOW_STOPPED or smm.pit_limiter == 1):
					if(time() - blink_last >= blink_duration*2):
						blink_last = time()
					if(time() - blink_last <= blink_duration):
						status[3] = '1'
					if(time() - blink_last > blink_duration):
						status[3] = '0'
						dash.right = 'pit '
				# blink green RPM LED and DRS on display while DRS engaged (untested)
				if(smm.drs_engaged == 1):
					if(time() - blink_last >= blink_duration*2):
						blink_last = time()
					if(time() - blink_last <= blink_duration):
						dash.rpm['green'] = '0110'
						dash.left = 'drs '
						dash.right = ' on '
					if(time() - blink_last > blink_duration):
						dash.rpm['green'] = '1001'
				# blink green RPM LED during PTP cool-down, charging effect on last 4 seconds
				if(smm.push_to_pass.amount_left > 0):
					if(smm.push_to_pass.wait_time_left <= 4):
						dash.rpm['green'] = ('0'*(int(smm.push_to_pass.wait_time_left))).rjust(4, '1')
					else:
						if(time() - blink_last >= blink_duration*2):
							blink_last = time()
						if(time() - blink_last <= blink_duration):
							dash.rpm['green'] = '1000'
						if(time() - blink_last > blink_duration):
							dash.rpm['green'] = '0001'
				# blink green RPM LED during PTP engaged, depleting effect on last 4 seconds
				# blink PTP activations remaining on display while PTP engaged
				if(smm.push_to_pass.engaged == 1):
					if(smm.push_to_pass.engaged_time_left <= 4):
						dash.rpm['green'] = ('1'*(int(smm.push_to_pass.engaged_time_left))).rjust(4, '0')
					else:
						if(time() - blink_last >= blink_duration*2):
							blink_last = time()
						if(time() - blink_last <= blink_duration):
							dash.rpm['green'] = '0110'
							dash.left = ' ptp'
							dash.right = str(smm.push_to_pass.amount_left).ljust(4)
						if(time() - blink_last > blink_duration):
							dash.rpm['green'] = '1001'
				dash.status = ''.join(status)
				# make sure engine is running
				if(smm.engine_rps > 0):
					dash.update()
				else:
					dash.reset()
				
			log_print(lfh, "Closing shared memory map...")
			r3e_smm_handle.close()
		except:
			log_print(lfh, "Unhandled exception!")
			log_print(lfh, format_exc())
