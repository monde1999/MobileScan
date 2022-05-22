from numpy import dtype
import requests
import json
import glob
import time

from PIL import Image
import matplotlib.pyplot  as plt
import open3d as o3d
import numpy as np

rgbs = glob.glob('dataset2/rgb/*.jpg')
depths = glob.glob('dataset2/depth/*.png')
confs = glob.glob('dataset2/conf/*.png')

rgbs.sort()
depths.sort()
confs.sort()

print(len(rgbs), len(depths), len(confs))

max = 200
rgbs = rgbs[:max]
depths = depths[:max]
confs = confs[:max]

# for rgb, d in zip(rgbs,depths):
#     f, axs = plt.subplots(1,2)
#     axs[0].imshow(np.array(Image.open(rgb), dtype=np.uint8))
#     axs[1].imshow(np.array(Image.open(d), dtype=np.uint16))
#     plt.show()

url = 'http://127.0.0.1:8000/modeler/integrate/'
fn = 1
for rgb, depth, conf in zip(rgbs, depths, confs):
    files = {'rgb': open(rgb, 'rb'), 'depth': open(depth, 'rb'), 'conf': open(conf, 'rb')}
    data = {'fn': fn}
    res = requests.post(url, data=data, files = files)
    fn += 1
    print('sending %s: %s' % (rgb, res))

# url = 'http://127.0.0.1:8000/modeler/go/'
# print('go...')
# res = requests.get(url)