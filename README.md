# pySRD9c

A Python test application for the Renovatio SRD-9c display (http://www.renovatio-dev.com/).

This small application makes use of the pywinusb module (https://github.com/rene-aguirre/pywinusb) to interface with the SRD-9c display. The display uses the HID protocol to provide an input interface as a joystick and an output interface for the nine 7-segment displays and 16 LEDs. 

The output report is structured as follows (41 bytes total):

report id: 1 byte, always 0 as this is the only output report
left display: 4 bytes, each bit is a single segment of the display in the standard order (4 digits)
right display: 4 bytes, each bit is a single segment of the display in the standard order (4 digits)
green/red RPM LEDs: 1 byte, the four low bits are the green LEDs, the four high bits are the red LEDs
blue/status LEDs: 1 byte, the four low bits are the blue RPM LEDs, the four high bits are the status LEDS (low to high: red, yellow, blue, green)
gear display: 1 byte, each bit is a single segment of the display in the standard order (1 digit)
padding/unknown: 29 bytes, all 0 during normal operation, setting all bytes to 0xff resets the device

### Releases
#### 2016-05-02

* Initial release
