# -*- coding: utf-8 -*-

import settings
from pathlib2 import *
import requests

src_path = '/Users/allovince'

files = Path(src_path).glob('**/*.docx')

for file in files:
    print(file)