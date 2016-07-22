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
import requests
from pkg_resources import parse_version
from win32com.shell.shell import ShellExecuteEx
from win32com.shell import shellcon
from subprocess import check_output

plugin_dll = "rFactorSharedMemoryMap.dll"
github_api_url = 'https://api.github.com/repos/dallongo/rFactorSharedMemoryMap/releases'
steam_app_id = '431600'
steam_app_id_file = 'steam_appid.txt'

APP_NAME = 'pluginInstaller'
APP_VER = '1.0.0.0'
APP_DESC = 'Downloads and installs {0} plugin for Automobilista'.format(plugin_dll)
APP_AUTHOR = 'Dan Allongo (daniel.s.allongo@gmail.com)'
APP_URL = 'https://github.com/dallongo/pySRD9c/pyinstaller'

def is_admin():
  try:
    return ctypes.windll.shell32.IsUserAnAdmin()
  except:
    return False

def run_as_admin():
  procInfo = ShellExecuteEx(nShow=win32con.SW_SHOWNORMAL,
                            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                            lpVerb='runas',
                            lpFile=sys.executable)
  procHandle = procInfo['hProcess']    
  obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)

  return win32process.GetExitCodeProcess(procHandle)

if __name__ == "__main__":
  print "{0} v.{1}".format(APP_NAME, APP_VER)
  print APP_DESC
  print APP_AUTHOR
  print APP_URL
  print

  if os.name != 'nt':
    raise RuntimeError, "This program is for Windows only"

  if not is_admin():
    print "This program requires administrator privileges"
    sys.exit(run_as_admin())
  print "Finding latest release in {0}".format(github_api_url)
  r = requests.get(github_api_url)
  if r.status_code != 200:
    print "Error: unable to make GitHub API call!"
    os.system('pause')
    sys.exit(1)
  repo_info = r.json()
  latest_release = None
  download_url = None
  download_size = None
  for rel in repo_info:
    if not latest_release or parse_version(rel['tag_name']) > parse_version(latest_release['tag_name']):
      latest_release = rel
      asset = [a for a in latest_release['assets'] if a['name'] == plugin_dll]
      if asset:
        download_url = asset[0]['browser_download_url']
        download_size = asset[0]['size']
  if not latest_release or not download_url:
    print "Error: unable to find latest release!"
    os.system('pause')
    sys.exit(1)
  print "Using latest release {0}".format(latest_release['tag_name'])
  print "Downloading asset at {0}".format(download_url)
  r = requests.get(download_url)
  if r.status_code != 200:
    print "Error: unable to download asset!"
    os.system('pause')
    sys.exit(1)
  with open(plugin_dll, 'wb') as f:
    f.write(r.content)
  if os.stat(plugin_dll).st_size != download_size:
    print "Error: incomplete download, expected {1}, got {2}!".format(download_size, os.stat(plugin_dll).st_size)
    os.system('pause')
    sys.exit(1)
  print "Successfully downloaded {0}".format(plugin_dll)
  print "Searching registry for Automobilista install path..."
  try:
    ams_install_path = os.path.join(check_output('reg query HKLM\\Software /s /f "Steam App {0}" /v InstallLocation /k /e /t REG_SZ /c'.format(steam_app_id), shell=True).split('REG_SZ    ')[1].split('\r\n')[0],'Plugins')
  except:
    print "Searching disks for Automobilista install path..."
    for drive in win32api.GetLogicalDriveStrings().split('\x00')[1::-1]:
      for root,path,files in os.walk(drive):
        head, tail = os.path.split(root)
        if tail == 'Automobilista' and 'AMS.exe' in files and steam_app_id_file in files:
          with open(os.path.join(root,steam_app_id_file),'r') as f:
            app_id = f.read()
          if app_id == steam_app_id:
            ams_install_path = os.path.join(root,'Plugins')
            break
    if not ams_install_path:
      print "Unable to locate Automobilista install path!"
      os.system('pause')
      sys.exit(1)
  if os.path.exists(ams_install_path):
    print "Found Automobilista plugin path in {0}".format(ams_install_path)
  else:
    print "Unable to locate Automobilista plugin path, please copy {0} manually to Plugins folder.".format(plugin_dll)
    os.system('pause')
    sys.exit(1)
  try:
    shutil.copy(plugin_dll, ams_install_path)
    print "{0} successfully copied to {1}".format(plugin_dll, ams_install_path)
  except:
    traceback.print_exc()
    print "Unable to copy {0} to {1}".format(plugin_dll, ams_install_path)
    os.system('pause')
    sys.exit(1)
  print
  print "Done!"
  print
  os.system('pause')
  sys.exit(0)
