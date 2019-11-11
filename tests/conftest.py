# This setup is necessary as "tests/" folder is not inside "app/"

import os
import sys


latigo_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/"))


sys.path.insert(0, latigo_path)
sys.path.insert(0, "/private/lroll/Desktop/ioc_client/latigo/app/latigo")
sys.path.insert(0, "/private/lroll/Desktop/ioc_client/latigo/app")
