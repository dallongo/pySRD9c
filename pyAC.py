"""
pyAC.py - Defines the shared memory map structures for Assetto Corsa
by Dan Allongo (daniel.s.allongo@gmail.com)

Release History:
2016-07-05: Initial release
"""

from ctypes import *

class acStruct(Structure):
	_pack_ = 4

class acStatusEnum(acStruct):
	_fields_ = [('off', c_int),
				('replay', c_int),
				('live', c_int),
				('pause', c_int)]
acStatus = acStatusEnum(0, 1, 2, 3)

class acSessionEnum(acStruct):
	_fields_ = [('unknown', c_int),
				('practice', c_int),
				('qualify', c_int),
				('race', c_int),
				('hotlap', c_int),
				('timeAttack', c_int),
				('drift', c_int),
				('drag', c_int)]
acSession = acSessionEnum(-1, 0, 1, 2, 3, 4, 5, 6)

class acFlagEnum(acStruct):
	_fields_ = [('none', c_int),
				('blue', c_int),
				('yellow', c_int),
				('black', c_int),
				('white', c_int),
				('checkered', c_int),
				('penalty', c_int)]
acFlag = acFlagEnum(0, 1, 2, 3, 4, 5, 6)

class acPhysics(acStruct):
	_fields_ = [('packetId', c_int), 
				('gas', c_float), 
				('brake', c_float), 
				('fuel', c_float), 
				('gear', c_int), 
				('rpm', c_int), 
				('steerAngle', c_float), 
				('speed', c_float), 
				('velocity', c_float*3), 
				('accG', c_float*3), 
				('wheelSlip', c_float*4), 
				('wheelLoad', c_float*4), 
				('tirePressure', c_float*4), 
				('wheelAngularVelocity', c_float*4), 
				('tireWear', c_float*4), 
				('tireDirtLevel', c_float*4), 
				('tireTemperature', c_float*4), 
				('camber', c_float*4), 
				('suspensionTravel', c_float*4), 
				('drs', c_float), 
				('tc', c_float), 
				('heading', c_float), 
				('pitch', c_float), 
				('roll', c_float), 
				('cgHeight', c_float), 
				('damage', c_float*5), 
				('wheelsOffTrack', c_int), 
				('pitLimiter', c_int), 
				('abs', c_float), 
				('kersCharge', c_float), 
				('kersInput', c_float), 
				('autoShifterOn', c_int), 
				('rideHeight', c_float*2), 
				('turboBoost', c_float), 
				('ballast', c_float), 
				('airDensity', c_float), 
				('airTemperature', c_float), 
				('trackTemperature', c_float), 
				('localAngularVelocity', c_float*3), 
				('finalFF', c_float)]

class acGraphics(acStruct):
	_fields_ = [('packetId', c_int), 
				('status', c_int), 
				('session', c_int), 
				('currentTime', c_wchar*15), 
				('lastTime', c_wchar*15), 
				('bestTime', c_wchar*15), 
				('split', c_wchar*15), 
				('completedLaps', c_int), 
				('position', c_int), 
				('iCurrentTime', c_int), 
				('iLastTime', c_int), 
				('iBestTime', c_int), 
				('sessionTimeLeft', c_float), 
				('distanceTraveled', c_float), 
				('inPit', c_int), 
				('currentSector', c_int), 
				('lastSectorTime', c_int), 
				('numberOfLaps', c_int), 
				('tireCompound', c_wchar*33), 
				('replayTimeMultiplier', c_float), 
				('normalizedPosition', c_float), 
				('coordinates', c_float*3), 
				('penaltyTime', c_float), 
				('flag', c_int), 
				('idealLine', c_int), 
				('inPitLane', c_int), 
				('surfaceGrip', c_float)]

class acStatic(acStruct):
	_fields_ = [('smVersion', c_wchar*15), 
				('acVersion', c_wchar*15), 
				('numberOfSessions', c_int), 
				('numCars', c_int), 
				('carModel', c_wchar*33), 
				('track', c_wchar*33), 
				('playerName', c_wchar*33), 
				('playerSurname', c_wchar*33), 
				('playerNick', c_wchar*33), 
				('sectorCount', c_int), 
				('maxTorque', c_float), 
				('maxPower', c_float), 
				('maxRPM', c_int), 
				('maxFuel', c_float), 
				('suspensionMaxTravel', c_float*4), 
				('tireRadius', c_float*4), 
				('maxTurboBoost', c_float), 
				('unused1', c_float), 
				('unused2', c_float), 
				('penaltiesEnabled', c_int), 
				('aidFuelRate', c_float), 
				('aidTireRate', c_float), 
				('aidDamageRate', c_float), 
				('aidTireBlankets', c_int), 
				('aidStability', c_float), 
				('aidAutoClutch', c_int), 
				('aidAutoBlip', c_int)]

def kph_to_mph(m):
	return (m * 1.60934)

def mps_to_kph(m):
	return (m * 3.6)

def kpa_to_psi(k):
	return (k * 0.145038)

def c_to_f(c):
	return (c * 1.8) + 32

def l_to_g(l):
	return (l * 0.264172)

acMapTag = {
	'physics':'Local\\acpmf_physics', 
	'graphics':'Local\\acpmf_graphics', 
	'static':'Local\\acpmf_static' 
}
acMapHandle = {
	'physics':None, 
	'graphics':None, 
	'static':None 
}
