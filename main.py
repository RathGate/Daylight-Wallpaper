import glob
import re

import requests
import json
from datetime import datetime, date, time, timezone
import os.path
import urllib3
import ctypes
from typing import List
import win32con
import pythoncom
import pywintypes
import win32gui
from win32com.shell import shell, shellcon

# Disable API call warnings:
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TimeData:
    def __init__(self, sunrise:datetime, sunset:datetime):
        self.sunrise = sunrise
        self.sunset = sunset
    def prettyPrint(self):
        print("    SUCCESS !\n    "
              f"Sunrise: {self.sunrise.strftime('%Hh%M')} UTC | "
              f"Sunset: {self.sunset.strftime('%Hh%M')} UTC")

    def getCurrentMode(self):
        now = datetime.now(timezone.utc)
        deltaSunrise, deltaSunset = getDeltaInMinutes(now, self.sunrise), getDeltaInMinutes(now, self.sunset)
        if -15 <= deltaSunrise <= 15:
            return "light"
        elif -15 <= deltaSunset <= 15:
            return "dark"
        elif self.sunrise <= now <= self.sunset:
            return "light"
        return "dark"

# Global variables
user32 = ctypes.windll.user32
current_tz = datetime.now().astimezone().tzinfo
defaultValues = {
    "latitude": 43.492029,
    "longitude": 5.169223,
    "sunrise": datetime.combine(date.today(), time(hour=7, tzinfo=current_tz)),
    "sunset": datetime.combine(date.today(), time(hour=19, tzinfo=current_tz)),
    "light": f'{os.path.dirname(os.path.abspath(__file__))}/wallpapers/light.png',
    "dark": f'{os.path.dirname(os.path.abspath(__file__))}/wallpapers/dark.png'
}

# Wallpaper transition animation functions
# From user "abdusco" on StackOverflow (question n°56973912)
def _make_filter(class_name: str, title: str):
    """https://docs.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumwindows"""

    def enum_windows(handle: int, h_list: list):
        if not (class_name or title):
            h_list.append(handle)
        if class_name and class_name not in win32gui.GetClassName(handle):
            return True  # continue enumeration
        if title and title not in win32gui.GetWindowText(handle):
            return True  # continue enumeration
        h_list.append(handle)

    return enum_windows
def find_window_handles(parent: int = None, window_class: str = None, title: str = None) -> List[int]:
    cb = _make_filter(window_class, title)
    try:
        handle_list = []
        if parent:
            win32gui.EnumChildWindows(parent, cb, handle_list)
        else:
            win32gui.EnumWindows(cb, handle_list)
        return handle_list
    except pywintypes.error:
        return []
def force_refresh():
    user32.UpdatePerUserSystemParameters(1)
def enable_activedesktop():
    """https://stackoverflow.com/a/16351170"""
    try:
        progman = find_window_handles(window_class='Progman')[0]
        cryptic_params = (0x52c, 0, 0, 0, 500, None)
        user32.SendMessageTimeoutW(progman, *cryptic_params)
    except IndexError as e:
        raise WindowsError('Cannot enable Active Desktop') from e
def set_wallpaper(image_path: str, use_activedesktop: bool = True):
    if use_activedesktop:
        enable_activedesktop()
    pythoncom.CoInitialize()
    iad = pythoncom.CoCreateInstance(shell.CLSID_ActiveDesktop,
                                     None,
                                     pythoncom.CLSCTX_INPROC_SERVER,
                                     shell.IID_IActiveDesktop)
    iad.SetWallpaper(str(image_path), 0)
    iad.ApplyChanges(shellcon.AD_APPLY_ALL)
    force_refresh()

def fileExists(date:datetime=datetime.now(), isToday:bool=True):
    if isToday:
        return os.path.isfile(f'timedata/saved_{date.strftime("%Y-%m-%d")}.json')
    for i in os.listdir('timedata/')[::-1]:
        if re.search("saved_202\d-\d{2}-\d{2}\.json", i):
            return i
    return False

def resetFolderContent(path:str):
    if not (os.path.exists(path)):
        os.makedirs(path)
        return
    files = glob.glob(path+"/*")
    for f in files:
        os.remove(f)

def convertDate(strdate:str):
    return datetime.fromisoformat(strdate)

def getDeltaInMinutes(base:datetime, comparison:datetime):
    delta = comparison.astimezone(timezone.utc) - base
    return round(delta.total_seconds() / 60)

def getDataFromAPI(lg=defaultValues["longitude"], lt=defaultValues["latitude"], saveInFile:bool=True):
    try:
        response = requests.get(f"https://api.sunrise-sunset.org/json?lat={lt}&lng={lg}&formatted=0", verify=False)

        # Checks for errors in response header:
        if response.status_code != 200:
            print("The API header status is not valid: " + response.status_code)
            return False

        # Parses the response body:
        body = json.loads(response.content)
        json_object = json.dumps(body, indent=4)

        # Checks for errors in response body:
        if body["status"] != "OK":
            print("The API content status is not valid.")
            return False

        if saveInFile:
            resetFolderContent("timedata")
            with open(f"timedata/saved_{datetime.now().strftime('%Y-%m-%d')}.json", "w") as outfile:
                outfile.write(json_object)

        return TimeData(convertDate(body["results"]["sunrise"]), convertDate(body["results"]["sunset"]))
    except:
        "Something went wrong when calling the API."
        return False

def getDataFromFile(filename:str=f"saved_{datetime.now().strftime('%Y-%m-%d')}.json"):
    try:
        with open(f"timedata/{filename}", "r") as file:
            data = json.load(file)
            return TimeData(convertDate(data["results"]["sunrise"]), convertDate(data["results"]["sunset"]))
    except:
        print("Couldn't read from the file")
        return False

def getTimeData():
    timedata = {}

    # 1. Checks for existing data already saved today
    print("1. Trying to fetch saved data for today...")
    if fileExists(datetime.now()):
        timedata = getDataFromFile()
        if timedata: return timedata
    print("    ERROR: No saved data found for today.")

    # 2. If not, calls the API and fetches data
    print("2. Trying to fetch data from API...")
    timedata = getDataFromAPI()
    if timedata: return timedata
    print("    ERROR: Couldn't get data from API.")

    # 3. If it fails, tries to fetch the latest saved data
    print("3. Trying to fetch the latest saved data...")
    alternativeFile = fileExists(isToday=False)
    if alternativeFile:
        timedata = getDataFromFile(alternativeFile)
        if timedata: return timedata
    print("   ERROR: No saved data found.")

    # 4. If it fails, uses the default values
    print("4. Using fallback values (7am - 7pm)...")
    return TimeData(defaultValues["sunrise"], defaultValues["sunset"])

def getCurrentWallpaperMode():
    ubuf = ctypes.create_unicode_buffer(512)
    user32.SystemParametersInfoW(win32con.SPI_GETDESKWALLPAPER, len(ubuf), ubuf, 0)
    currentWallpaperPath = (ubuf.value).replace("\\", "/")

    if currentWallpaperPath.endswith(f"/{str(defaultValues['light'])}"):
        return "light"
    elif currentWallpaperPath.endswith(f"/{str(defaultValues['dark'])}"):
        return "dark"
    return False

def main():
    timedata = getTimeData()
    timedata.prettyPrint()

    currentMode = timedata.getCurrentMode()
    test = getCurrentWallpaperMode();
    print(test)
    if currentMode != getCurrentWallpaperMode():
        print("Switching wallpapers.....")
        set_wallpaper(defaultValues[currentMode])

main()
