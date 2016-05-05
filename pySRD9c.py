"""
pySRD9c.py - A Python test application for the Renovatio SRD-9c display
by Dan Allongo (daniel.s.allongo@gmail.com)

This small application makes use of the pywinusb module (https://github.com/rene-aguirre/pywinusb)
to interface with the SRD-9c display. The display uses the HID protocol to provide an input interface
as a joystick and an output interface for the nine 7-segment displays and 16 LEDs. 

The output report is structured as follows (41 bytes total):
report id: 1 byte, always 0 as this is the only output report
left display: 4 bytes, each bit is a single segment of the display in the standard order (4 digits)
right display: 4 bytes, each bit is a single segment of the display in the standard order (4 digits)
green/red RPM LEDs: 1 byte, the four low bits are the green LEDs, the four high bits are the red LEDs
blue/status LEDs: 1 byte, the four low bits are the blue RPM LEDs, the four high bits are the 
	status LEDS (low to high: red, yellow, blue, green)
gear display: 1 byte, each bit is a single segment of the display in the standard order (1 digit)
padding/unknown: 29 bytes, all 0 during normal operation, setting all bytes to 0xff resets the device

Release History:
2016-05-04: Added sanity checks, helper functions, friendlier LED handling
2016-05-02: Initial release
"""

from pywinusb import hid
from time import sleep

class srd9c:
	lut = {
	 '0':int('00111111', 2),
	 '1':int('00000110', 2),
	 '2':int('01011011', 2),
	 '3':int('01001111', 2),
	 '4':int('01100110', 2),
	 '5':int('01101101', 2),
	 '6':int('01111101', 2),
	 '7':int('00000111', 2),
	 '8':int('01111111', 2),
	 '9':int('01101111', 2),
	 'A':int('01110111', 2),
	 'B':int('01111100', 2),
	 'C':int('01011000', 2),
	 'D':int('01011110', 2),
	 'E':int('01111001', 2),
	 'F':int('01110001', 2),
	 'G':int('00111101', 2),
	 'H':int('01110100', 2),
	 'I':int('00010000', 2),
	 'J':int('00001110', 2),
	 'L':int('00111000', 2),
	 'N':int('01010100', 2),
	 'O':int('01011100', 2),
	 'P':int('01110011', 2),
	 'Q':int('01101011', 2),
	 'R':int('01010000', 2),
	 'S':int('01101101', 2),
	 'T':int('01111000', 2),
	 'U':int('00011100', 2),
	 'Y':int('01101110', 2),
	 'Z':int('01011011', 2),
	 '-':int('01000000', 2),
	 '_':int('00001000', 2),
	 '=':int('01001000', 2),
	 '"':int('00100010', 2),
	 "'":int('00100000', 2),
	 '`':int('00000010', 2),
	 '.':int('10000000', 2)
	}

	def __init__(self, init_left='-'*4, init_right='-'*4, init_gear='-', use_green=True, use_red=True, use_blue=True, use_status=False):
		self.device = None
		self.output_report = None
		self.left = init_left
		self.right = init_right
		self.gear = init_gear
		self.rpm = {'green':'0'*4, 'red':'0'*4, 'blue':'0'*4, 
			'use_green':use_green, 'use_red':use_red, 'use_blue':use_blue, 'use_status':use_status,
			'value':0}
		self.status = '0'*4
		while(not self.device):
			devlist = hid.HidDeviceFilter(vendor_id = 0x04d8, product_id = 0xf667).get_devices()
			if(devlist):
				self.device = devlist[0]
				self.device.open()
				self.output_report = self.device.find_output_reports()[0]
			else:
				sleep(1)
		self.update()
		return

	def string_to_display(self, s='-'*4, l=4):
		o = []
		while(len(s.replace('.', '')) > l):
			s = s[:-1]
		while(len(s.replace('.', '')) < l):
			s = ' ' + s
		for i in xrange(len(s)):
			c = s[i].upper()
			if c == '.':
				continue
			if c in self.lut:
				c = self.lut[c]
			else:
				c = 0
			if (i < len(s) - 1) and s[i + 1] == '.':
				c += self.lut['.']
			o.append(c)
		return o

	def string_to_led(self, s='0'*4):
		return ''.join([i for i in s if i in ['0', '1']]).rjust(4, '0')[3::-1]

	def calc_leds(self):
		rpm_on = 1
		rpm_leds = 0
		if(self.rpm['value'] < 0):
			rpm_on = 0
		rpm_leds = (int(self.rpm['use_green']) + int(self.rpm['use_red']) + int(self.rpm['use_blue']) + int(self.rpm['use_status']))*4
		rpm = (str(rpm_on)*(int(rpm_leds*abs(self.rpm['value'])))).ljust(rpm_leds, str(rpm_on^1))
		if(self.rpm['use_green']):
			self.rpm['green'] = rpm[:4]
			rpm = rpm[4:]
		if(self.rpm['use_red']):
			self.rpm['red'] = rpm[:4]
			rpm = rpm[4:]
		if(self.rpm['use_blue']):
			self.rpm['blue'] = rpm[:4]
			rpm = rpm[4:]
		if(self.rpm['use_status']):
			self.status = rpm[:4]
		return

	def pack_report(self):
		self.calc_leds()
		o = [0]
		o += self.string_to_display(self.left, 4)
		o += self.string_to_display(self.right, 4)
		o += [int(self.string_to_led(self.rpm['red']) + self.string_to_led(self.rpm['green']), 2)]
		o += [int(self.string_to_led(self.status) + self.string_to_led(self.rpm['blue']), 2)]
		o += self.string_to_display(self.gear, 1)
		o += [0]*(41 - len(o))
		return o

	def update(self):
		self.output_report.send(self.pack_report())
		return

	def reset(self):
		self.gear = '-'
		self.left = '-'*4
		self.right = '-'*4
		self.rpm['value'] = 0
		self.rpm['green'] = '0'*4
		self.rpm['red'] = '0'*4
		self.rpm['blue'] = '0'*4
		self.status = '0'*4
		self.update()
		return

	def self_test(self):
		self.gear = '0'
		self.left = 'self'
		self.right = 'test'
		self.rpm['value'] = 0
		while(True):
			if(self.rpm['value'] >= 1):
				break
			self.rpm['value'] += 0.01
			self.update()
			sleep(0.01)
		self.left = 'done'
		self.right = ' '*4
		self.gear = ' '
		self.update()
		sleep(1)
		self.reset()
		return


if __name__ == '__main__':
	print "Waiting for device..."
	test = srd9c(init_left='srd9', init_gear='c', init_right='init', use_status=True)
	print "Device found!"
	sleep(3)
	print "Beginning test cycle..."
	test.self_test()
	print "Done!"
