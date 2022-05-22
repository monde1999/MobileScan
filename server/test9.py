import glob
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

rgbs = glob.glob('dataset2/rgb/*.jpg')
depths = glob.glob('dataset2/depth/*.png')
confs = glob.glob('dataset2/conf/*.png')

rgbs.sort()
depths.sort()
confs.sort()

print(len(rgbs), len(depths), len(confs))

max = 10
rgbs = rgbs[:max]
depths = depths[:max]
confs = confs[:max]

rgb = rgbs[0]
depth = depths[0]
conf = confs[0]

rgb = Image.open(rgb)
depth = Image.open(depth)
conf = Image.open(conf)

rgb = np.asarray(rgb)
#rgb = (rgb[:, :, 0] + rgb[:, :, 1] + rgb[:, :, 2]) // 3  # grayscale
depth = np.asarray(depth)
conf = np.asarray(conf)

mask = depth > 1100
depth2 = depth.copy()
depth2[mask] = 0
rgb[mask] = [0,0,0]
conf[mask] = 0
th = 255 * 0.8
th = int(th)
mask2 = conf<th
conf[mask2] = 0
rgb[mask2] = [0,0,0]

_, axs = plt.subplots(1,4)
axs[0].imshow(rgb, cmap='gray')
axs[1].imshow(depth)
axs[2].imshow(conf)
axs[3].imshow(depth2)
plt.show()