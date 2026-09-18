import requests
import json
from bs4 import BeautifulSoup

res = requests.get('https://www.apple.com/shop/refurbished/mac/2019-27-inch-imac')
s = BeautifulSoup(res.text)
scripts = s.findAll('script')
scr = scripts[22]   # probably need to search for keyword here
c = scr.contents[0]
j = c[c.index('{'):c.rfind('}')+1]
d = json.loads(j)

#[(i, p) for i,p in enumerate(d['products'])
# if p['dimensions'].get('refurbClearModel','')=='imac'
# and p['dimensions'].get('dimensionScreensize','')=='27inch'
# and p['dimensions'].get('dimensionRelYear','')=='2019']

[(t['title'], t['price']['currentPrice']) for t in d['tiles']
 if t.get('title','').find('i9') >= 0 and
 t.get('title','').find('iMac') >= 0 and
 t.get('title','').find('27-inch') >= 0 and
 t['filters']['dimensions']['dimensionRelYear']=='2019']
