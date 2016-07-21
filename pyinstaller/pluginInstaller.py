import sys
import traceback
import ctypes
import os
import os.path
import win32api
import win32con
import win32event
import win32process
import shutil
from win32com.shell.shell import ShellExecuteEx
from win32com.shell import shellcon
from subprocess import check_output

def is_admin():
  if os.name != 'nt':
    raise RuntimeError, "This program is for Windows only"
  try:
    return ctypes.windll.shell32.IsUserAnAdmin()
  except:
    traceback.print_exc()
    return False

def run_as_admin():
  if os.name != 'nt':
    raise RuntimeError, "This program is for Windows only"
  
  procInfo = ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
                            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                            lpVerb='runas',
                            lpFile=sys.executable)
  procHandle = procInfo['hProcess']    
  obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)

  return win32process.GetExitCodeProcess(procHandle)

if __name__ == "__main__":
  if not is_admin():
    print "This program requires administrator privileges"
    sys.exit(run_as_admin())
  try:
    ams_install_path = check_output('reg query HKLM\\Software /s /f "Steam App 431600" /v InstallLocation /k /e /t REG_SZ /c', shell=True).split('REG_SZ    ')[1].split('\r\n')[0] + '\\Plugins'
  except:
    traceback.print_exc()
    print "Unable to locate Automobilista install path!"
    os.system('pause')
    sys.exit(1)
  if os.path.exists(ams_install_path):
    print "Found Automobilista plugin path in {0}".format(ams_install_path)
  else:
    print "Unable to locate Automobilista plugin path!"
    os.system('pause')
    sys.exit(1)
  plugin_dll = "rFactorSharedMemoryMap.dll"
  try:
    shutil.copy(plugin_dll, ams_install_path)
    print "{0} successfully copied to {1}".format(plugin_dll, ams_install_path)
  except:
    traceback.print_exc()
    print "Unable to copy {0} to {1}".format(plugin_dll, ams_install_path)
    os.system('pause')
    sys.exit(1)
  os.system('pause')
  sys.exit(0)
