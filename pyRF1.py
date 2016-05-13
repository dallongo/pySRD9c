"""
pyRF1.py - Defines the shared memory map structures for rFactor
	as exported by rFactorSharedMemoryMap.dll
by Dan Allongo (daniel.s.allongo@gmail.com)

Release History:
2016-05-12: Added comments from rfSharedStruct.hpp
2016-05-09: Initial release
"""

from ctypes import *

class rfStruct(Structure):
	_pack_ = 1

class rfGamePhaseEnum(rfStruct):
	_fields_ = [('garage', c_int),
				('warmUp', c_int),
				('gridWalk', c_int),
				('formation', c_int),
				('countdown', c_int),
				('greenFlag', c_int),
				('fullCourseYellow', c_int),
				('sessionStopped', c_int),
				('sessionOver', c_int)]
rfGamePhase = rfGamePhaseEnum(0, 1, 2, 3, 4, 5, 6, 7, 8)

class rfYellowFlagStateEnum(rfStruct):
	_fields_ = [('invalid', c_int),
				('noFlag', c_int),
				('pending', c_int),
				('pitClosed', c_int),
				('pitLeadLap', c_int),
				('pitOpen', c_int),
				('lastLap', c_int),
				('resume', c_int),
				('raceHalt', c_int)]
rfYellowFlagState = rfYellowFlagStateEnum(-1, 0, 1, 2, 3, 4, 5, 6, 7)

class rfSurfaceTypeEnum(rfStruct):
	_fields_ = [('dry', c_int),
				('wet', c_int),
				('grass', c_int),
				('dirt', c_int),
				('gravel', c_int),
				('kerb', c_int)]
rfSurfaceType = rfSurfaceTypeEnum(0, 1, 2, 3, 4, 5)

class rfSectorEnum(rfStruct):
	_fields_ = [('sector3', c_int),
				('sector1', c_int),
				('sector2', c_int)]
rfSector = rfSectorEnum(0, 1, 2)

class rfFinishStatusEnum(rfStruct):
	_fields_ = [('none', c_int),
				('finished', c_int),
				('dnf', c_int),
				('dq', c_int)]
rfFinishStatus = rfFinishStatusEnum(0, 1, 2, 3)

class rfControlEnum(rfStruct):
	_fields_ = [('nobody', c_int),
				('player', c_int),
				('ai', c_int),
				('remote', c_int),
				('replay', c_int)]
rfControl = rfControlEnum(-1, 0, 1, 2, 3)

class rfWheelIndexEnum(rfStruct):
	_fields_ = [('frontLeft', c_int),
				('frontRight', c_int),
				('rearLeft', c_int),
				('rearRight', c_int)]
rfWheelIndex = rfWheelIndexEnum(0, 1, 2, 3)

class rfVec3(rfStruct):
	_fields_ = [('x', c_float),
				('y', c_float),
				('z', c_float)]

class rfWheel(rfStruct):
	_fields_ = [('rotation', c_float),			# radians/sec
				('suspensionDeflection', c_float),# meters
				('rideHeight', c_float),		# meters
				('tireLoad', c_float),			# Newtons
				('lateralForce', c_float),		# Newtons
				('gripFract', c_float),			# an approximation of what fraction of the contact patch is sliding
				('brakeTemp', c_float),			# Celsius
				('pressure', c_float),			# kPa
				('temperature', c_float*3),		# Celsius, left/center/right (not to be confused with inside/center/outside!)
				('wear', c_float),				# wear (0.0-1.0, fraction of maximum) ... this is not necessarily proportional with grip loss
				('terrainName', c_char*16),		# the material prefixes from the TDF file
				('surfaceType', c_int8),		# rfSurfaceType
				('flat', c_bool),				# whether tire is flat
				('detached', c_bool)]			# whether wheel is detached

# only updated every 0.5 seconds (interpolated when deltaTime > 0)
class rfVehicleInfo(rfStruct):
	_fields_ = [('driverName', c_char*32),		# driver name
				('vehicleName', c_char*64),		# vehicle name
				('totalLaps', c_short),			# laps completed
				('sector', c_int8),				# rfSector
				('finishStatus', c_int8),		# rfFinishStatus
				('lapDist', c_float),			# current distance around track
				('pathLateral', c_float),		# lateral position with respect to *very approximate* "center" path
				('trackEdge', c_float),			# track edge (w.r.t. "center" path) on same side of track as vehiclev
				('bestSector1', c_float),		# best sector 1
				('bestSector2', c_float),		# best sector 2 (plus sector 1)
				('bestLapTime', c_float),		# best lap time
				('lastSector1', c_float),		# last sector 1
				('lastSector2', c_float),		# last sector 2 (plus sector 1)
				('lastLapTime', c_float),		# last lap time
				('curSector1', c_float),		# current sector 1 if valid
				('curSector2', c_float),		# current sector 2 (plus sector 1) if valid
				('numPitstops', c_short),		# number of pitstops made
				('numPenalties', c_short),		# number of outstanding penalties
				('isPlayer', c_bool),			# is this the player's vehicle
				('control', c_int8),			# rfControl
				('inPits', c_bool),				# between pit entrance and pit exit (not always accurate for remote vehicles)
				('place', c_int8),				# 1-based position
				('vehicleClass', c_char*32),	# vehicle class
				('timeBehindNext', c_float),	# time behind vehicle in next higher place
				('lapsBehindNext', c_long),		# laps behind vehicle in next higher place
				('timeBehindLeader', c_float),	# time behind leader
				('lapsBehindLeader', c_long),	# laps behind leader
				('lapStartET', c_float),		# time this lap was started
				('pos', rfVec3),				# world position in meters
				('localVel', rfVec3),			# velocity (meters/sec) in local vehicle coordinates
				('localAccel', rfVec3),			# acceleration (meters/sec^2) in local vehicle coordinates
				('oriX', rfVec3),				# top row of orientation matrix (also converts local vehicle vectors into world X using dot product)
				('oriY', rfVec3),				# mid row of orientation matrix (also converts local vehicle vectors into world Y using dot product)
				('oriZ', rfVec3),				# bot row of orientation matrix (also converts local vehicle vectors into world Z using dot product)
				('localRot', rfVec3),			# rotation (radians/sec) in local vehicle coordinates
				('localRotAccel', rfVec3),		# rotational acceleration (radians/sec^2) in local vehicle coordinates
				('speed', c_float)]				# meters/sec

class rfShared(rfStruct):
	_fields_ = [('deltaTime', c_float),			# time since last scoring update (seconds)
				('lapNumber', c_long),			# current lap number
				('lapStartET', c_float),		# time this lap was started
				('vehicleName', c_char*64),		# current vehicle name
				('trackName', c_char*64),		# current track name
				('pos', rfVec3),				# world position in meters
				('localVel', rfVec3),			# velocity (meters/sec) in local vehicle coordinates
				('localAccel', rfVec3),			# acceleration (meters/sec^2) in local vehicle coordinates
				('oriX', rfVec3),				# top row of orientation matrix (also converts local vehicle vectors into world X using dot product)
				('oriY', rfVec3),				# mid row of orientation matrix (also converts local vehicle vectors into world Y using dot product)
				('oriZ', rfVec3),				# bot row of orientation matrix (also converts local vehicle vectors into world Z using dot product)
				('localRot', rfVec3),			# rotation (radians/sec) in local vehicle coordinates
				('localRotAccel', rfVec3),		# rotational acceleration (radians/sec^2) in local vehicle coordinates
				('speed', c_float),				# meters/sec
				('gear', c_long),				# -1=reverse, 0=neutral, 1+=forward gears
				('engineRPM', c_float),			# engine RPM
				('engineWaterTemp', c_float),	# Celsius
				('engineOilTemp', c_float),		# Celsius
				('clutchRPM', c_float),			# clutch RPM
				('unfilteredThrottle', c_float),# ranges  0.0-1.0
				('unfilteredBrake', c_float),	# ranges  0.0-1.0
				('unfilteredSteering', c_float),# ranges -1.0-1.0 (left to right)
				('unfilteredClutch', c_float),	# ranges  0.0-1.0
				('steeringArmForce', c_float),	# force on steering arms
				('fuel', c_float),				# amount of fuel (liters)
				('engineMaxRPM', c_float),		# rev limit
				('scheduledStops', c_int8),		# number of scheduled pitstops
				('overheating', c_bool),		# whether overheating icon is shown
				('detached', c_bool),			# whether any parts (besides wheels) have been detached
				('dentSeverity', c_int8*8),		# dent severity at 8 locations around the car (0=none, 1=some, 2=more)
				('lastImpactET', c_float),		# time of last impact
				('lastImpactMagnitude', c_float),# magnitude of last impact
				('lastImpactPos', rfVec3),		# location of last impact
				('wheel', rfWheel*4),			# rfWheelIndex

				# below this line is only updated every 0.5 seconds! (interpolated when deltaTime > 0)
				('session', c_long),			# current session
				('currentET', c_float),			# current time
				('endET', c_float),				# ending time
				('maxLaps', c_long),			# maximum laps
				('lapDist', c_float),			# distance around track
				('numVehicles', c_long),		# current number of vehicles
				('gamePhase', c_int8),			# rfGamePhase
				('yellowFlagState', c_int8),	# rfYellowFlagState
				('sectorFlag', c_int8*3),		# whether there are any local yellows at the moment in each sector
				('startLight', c_int8),			# start light frame (number depends on track)
				('numRedLights', c_int8),		# number of red lights in start sequence
				('inRealtime', c_bool),			# in realtime as opposed to at the monitor
				('playerName', c_char*32),		# player name (including possible multiplayer override)
				('plrFileName', c_char*64),		# may be encoded to be a legal filename
				('ambientTemp', c_float),		# Celsius
				('trackTemp', c_float),			# Celsius
				('wind', rfVec3),				# wind speed
				('vehicle', rfVehicleInfo*128)]	# array of vehicle scoring info

def mps_to_mph(m):
	return (m * 2.23694)

def mps_to_kph(m):
	return (m * 3.6)

def kpa_to_psi(k):
	return (k * 0.145038)

def c_to_f(c):
	return (c * 1.8) + 32

def l_to_g(l):
	return (l * 0.264172)

rfMapTag = '$rFactorShared$'
rfMapHandle = None
