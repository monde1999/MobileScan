from calendar import c
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

r0 = np.array(Image.open('temp/rgb/c00002.jpg'), dtype=np.uint8)
r0 = (r0[:, :, 0] + r0[:, :, 1] + r0[:, :, 2]) // 3  # grayscale
d0 = np.array(Image.open('temp/depth/d00002.png'), dtype=np.uint16)
c0 = np.array(Image.open('temp/conf/c00002.png'), dtype=np.uint8)

# r1 = r0[0:10,0:10]
# d1 = d0[0:10,0:10]
# c1 = c0[0:10,0:10]

depth = {}

i = 1
for r11, r12, r13 in zip(r0, d0, c0):
    for c11, c12, c13 in zip(r11, r12, r13):
        if c11 in depth:
            conf = depth[c11][1]
            if c13 > conf:
                depth[c11] = (c12, c13)
            elif c13 == conf:
                ave_depth = (depth[c11][0] + c12)//2
                depth[c11] = (ave_depth, c13)
        else:
            depth[c11] = (c12, c13)

keys = list(depth.keys())
keys.sort()
print(len(keys))

values0 = []
values1 = []

for k in keys:
    v0, v1 = depth[k]
    values0.append(v0)
    values1.append(v1)

d2 = d0.copy()
r = 0
while r<50:
    c = 0
    while c<80:
        # if r==5 and c==7:
        #     print('%d: %d --> %d' % (r1[r,c], d2[r,c], depth[r1[r,c]][0]))
        v1, v2 = depth[r0[r,c]]
        if v2!=0:
            d2[r,c] = v1
        c += 1
    r += 1

_, axs = plt.subplots(2,2)
axs[0,0].scatter(keys, values0)
axs[0,1].scatter(keys, values1)
axs[1,0].imshow(r0, cmap='gray')
axs[1,1].imshow(d2)
plt.show()