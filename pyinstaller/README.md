# pyDashR3E

by Dan Allongo (daniel.s.allongo@gmail.com)

A Python application that drives a Renovatio SRD-9c display (http://www.renovatio-dev.com/) using telemetry data from RaceRoom Racing Experience.

### Usage

Simply double-click to run, plug in the display, and then start R3E. The application requires read and write access in its current working directory for logging and settings file operations. Changes made to the settings file are detected while the application is running - no need to restart. That's it!

### Functions

* Green RPM LEDs - DRS/Push-to-Pass indicators, flashes 'drs' or 'ptp' on the left display when activated along with the number of activations remaining on the right display, otherwise used for 60%-73% RPM range
* Red RPM LEDs - Used for 74%-87% RPM range
* Blue RPM LEDs - Used for 88%-100% RPM range
* Left 4-digit LCD - Displays live timer for current lap (shows '-.--.-' for invalid/out laps)
* Center 1-digit LCD - Gear display
* Right 4-digit LCD - Displays current speed in mph
* Red status LED - Low fuel warning, turns on when 3 laps of fuel remain, blinks at 1 lap of fuel remaining and flashes 'fuel' on the left display
* Yellow status LED - High temperature warning, blinks when oil and/or water temperature is critical and flashes 'heat' on the left display
* Blue status LED - Shift light, comes on at 95% RPM range
* Green status LED - Pit window indicator, blinks when in pit or limiter activated and flashes 'pit' on the right display


* Lap time split - Completed lap time is held on the left display with the delta time (compared to the previous lap) on the right display
* Position - Current position shown on the left display with the total number of cars on the right display (shown after the lap time split)
* Laps - Completed laps shown on the left display with total number of laps (or session time remaining for timed sessions) on the right display (shown after the position display)
* Sector time split - Delta times for sectors 1 and 2 (compared to best sector times from all drivers in the session) are shown on the right display (shows '--.--' for invalid laps)

### Configuration

The file `pyDashR3E.settings.json` is created on first run.
Each of the functions can be enabled or disabled via the settings file.
It also includes additional comments on how each setting changes the display behavior.
Configuration changes made on the fly are detected as the application will re-read the settings file if it is modified while running.

### Known Issues

* Functions can be enabled or disabled but cannot be reassigned to different displays (ie, the speedometer and lap time displays cannot be switched, etc). The ability to fully customize the display and indicator locations is present in Renovatio's first-party software solution, so it's unnecessary to duplicate that functionality here. The main purpose of this application is to showcase capabilities not otherwise present in the first-party software.
* The RPM ranges for the LEDs are always linear and cannot be altered. This by design to maintain simplicity in the code.
* Fuel consumption and high temperature warnings are dynamic, being calculated based on the first 2 laps of the session (excluding the out lap). It's important to drive consistently in order for these functions to make appropriate estimates. As the application is storing this per-session calculation internally, restarting the application during an active session will result in incorrect estimates/unexpected behavior.
* Lap and sector time comparisons for 'self last lap' will not show if the immediately previous or current lap are invalidated or if the application is restarted during an active session. It will take 2 clean laps in succession to resync the session lap comparison.
* Sector 3 split times are never shown due to other important information being displayed upon crossing start/finish on each lap.
* The order of the information displays at the start of each lap cannot be changed (ie, lap time will always be first and laps/time remaining will always be last). This is by design to maintain simplicity in the code.
* DRS display functions have not been tested since I don't own any DTM 2013-2015 content. The Push-to-Pass functions have been tested thoroughly with the Audi Sport TT Cup 2015 car.

### Licensing and Distribution

This software is provided free of charge under the GPL v2 license.
The source code is available at https://github.com/dallongo/pySRD9c.

### Acknowledgements

Many thanks to the following folks:
* Renovatio Development - for making awesome hardware and top-notch displays
* Sector 3 Studios - for making a great sim and open-sourcing the sample implementation of their shared memory structure
* 'Mr. Belowski' - for making Crew Chief and helping me out with some of the calculations and structures
