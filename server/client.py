import requests
import json
import glob
import time

from PIL import Image
import matplotlib.pyplot  as plt
import open3d as o3d

rgbs = glob.glob('../../../../dataset/redwood/rgb/*.jpg')
depths = glob.glob('../../../../dataset/redwood/depth/*.png')

rgbs.sort()
depths.sort()

print(len(rgbs))

rgbs = rgbs[:100]
depths = depths[:100]

url = 'http://127.0.0.1:8000/modeler/integrate/'
for rgb, depth in zip(rgbs, depths):
    files = {'rgb': open(rgb, 'rb'), 'depth': open(depth, 'rb')}
    res = requests.post(url, files = files)
    print('sending %s: %s' % (rgb, res))

url = 'http://127.0.0.1:8000/modeler/go/'
print('go...')
res = requests.get(url)