import requests
import time
import webbrowser

#url = 'https://www.maimmunizations.org/'
url = 'https://www.macovidvaccines.com/'
while True:
    res = requests.get(url)
    if "you are now in line" in res.text:
        time.sleep(20)
    else:
        webbrowser.open(url)
