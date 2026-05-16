import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource (images/sounds), works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_data_path(filename):
    """ Get path to data files (JSON/CSV) so they save next to the EXE, not in temp """
    if getattr(sys, 'frozen', False):
        # If running as an EXE, use the folder containing the EXE
        base_path = os.path.dirname(sys.executable)
    else:
        # If running as a script, use the normal folder
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, filename)