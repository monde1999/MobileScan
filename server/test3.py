import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

r0 = np.array(Image.open('temp/rgb/c00000.jpg'), dtype=np.uint8)
d0 = np.array(Image.open('temp/depth/d00000.png'), dtype=np.uint16)
c0 = np.array(Image.open('temp/conf/c00000.png'), dtype=np.uint8)

r0 = (r0[:, :, 0] + r0[:, :, 1] + r0[:, :, 2]) // 3  # grayscale

"""
    assumptions:
        1. color image is accurate
    fix:
        1. Checkout the neighboring color pixels.
        2. Get the depth and confidence values of the neighbor pixel with closer similarities.
        3. Replace the depth of the current pixel with the highest confidence value.

"""
ROWS = 50
COLS = 80
ACR = 20  # acceptable color range
ADR = 50  # acceptable depth range
KERNEL = 3

r1 = np.pad(r0, KERNEL-2, mode='constant')
d1 = np.pad(d0, KERNEL-2, mode='constant')
c1 = np.pad(c0, KERNEL-2, mode='constant')

def get_data(r, c, color, depth, conf):
    return (color[r,c], depth[r,c], conf[r,c])

def get_neighbors(r, c, color, depth, conf):
    neighbors = []
    r1 = r-(KERNEL-2)
    while r1<r+(KERNEL-1):
        c1 = c-(KERNEL-2)
        while c1<c+(KERNEL-1):
            if r1!=r or c1!=c:
                neighbors.append(get_data(r1, c1, color, depth, conf))
            c1 += 1
        r1 += 1
    return neighbors

def fix(color, depth, conf):
    r = 1
    i = 1
    while r<=ROWS:
        c = 1
        while c<=COLS:
            data = get_data(r, c, color, depth, conf)
            neigbors = get_neighbors(r, c, color, depth, conf)
            # max_conf = -1
            # max_n = None
            ave_depth = 0
            ave_n = 0
            for n in neigbors:
                diff_color = abs(int(n[0]) - data[0])
                if diff_color < ACR and n[2]>=data[2]:
                    ave_depth += n[1]
                    ave_n += 1
                    # if max_conf < n[2]:
                    #     max_conf = n[2]
                    #     max_n = n
            if ave_n>0:
                ave_depth = ave_depth // ave_n
                # if ave_depth < max_n[1]-ADR:
                #     depth[r,c]  = max_n[1]-ADR
                # elif ave_depth > max_n[1]-ADR:
                #     depth[r,c]  = max_n[1]+ADR
                # else:
                depth[r,c] = ave_depth
                i+=1
            c += 1
        r += 1
    print(i, 'fixed')

for i in range(1):
    print(i+1, '...')
    fix(r1, d1, c1)

depth = d1[1:ROWS+1,1:COLS+1]
depth = Image.fromarray(depth)
depth.save('temp/fixed/depth.png')

# _, axs = plt.subplots(2,3)
# axs[0, 0].imshow(r0, cmap='gray')
# axs[0, 1].imshow(d0)
# axs[0, 2].imshow(c0, cmap='gray')
# axs[1, 0].imshow(r1, cmap='gray')
# axs[1, 1].imshow(d1)
# axs[1, 2].imshow(c1, cmap='gray')
# plt.show()