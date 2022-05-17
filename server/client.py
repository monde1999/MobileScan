from numpy import dtype
import requests
import json
import glob
import time

from PIL import Image
import matplotlib.pyplot  as plt
import open3d as o3d
import numpy as np

rgbs = glob.glob('temp/rgb/*.jpg')
depths = glob.glob('temp/depth/*.png')
confs = glob.glob('temp/conf/*.png')

rgbs.sort()
depths.sort()
confs.sort()

print(len(rgbs), len(depths), len(confs))

rgbs = rgbs[:200:20]
depths = depths[:200:20]
confs = confs[:200:20]

for rgb, d, c in zip(rgbs,depths,confs):
    f, axs = plt.subplots(1,3)
    axs[0].imshow(np.array(Image.open(rgb), dtype=np.uint8))
    axs[1].imshow(np.array(Image.open(d), dtype=np.uint16))
    axs[2].imshow(np.array(Image.open(c), dtype=np.uint8))
    plt.show()

# url = 'http://127.0.0.1:8000/modeler/integrate/'
# for rgb, depth in zip(rgbs, depths):
#     files = {'rgb': open(rgb, 'rb'), 'depth': open(depth, 'rb')}
#     res = requests.post(url, files = files)
#     print('sending %s: %s' % (rgb, res))

# url = 'http://127.0.0.1:8000/modeler/go/'
# print('go...')
# res = requests.get(url)