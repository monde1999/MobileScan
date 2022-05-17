import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import open3d as o3d
from modeler.z import *

fn = 1

r0 = Image.open('dataset/rgb/c%05d.jpg' % fn)
d0 = Image.open('dataset/depth/d%05d.png' % fn)
c0 = Image.open('dataset/conf/c%05d.png' % fn)

r0 = np.array(r0, dtype=np.uint8)
r01 = (r0[:, :, 0] + r0[:, :, 1] + r0[:, :, 2]) // 3  # grayscale
d0 = np.array(d0, dtype=np.uint16)
c0 = np.array(c0, dtype=np.uint8)

# _, axs = plt.subplots(1,3)
# axs[0].imshow(r01, cmap='gray')
# axs[1].imshow(d0)
# axs[2].imshow(c0)
# plt.show()

ROWS = 50
COLS = 80
ACR = 5  # acceptable color range
ADR = 50  # acceptable depth range
KERNEL = 3

r1 = np.pad(r01, KERNEL-2, mode='constant')
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
            ave_depth = int(data[1])
            ave_n = 1
            for n in neigbors:
                diff_color = abs(int(n[0]) - data[0])
                if diff_color < ACR and n[2]>=data[2]:
                    ave_depth += n[1]
                    ave_n += 1
            if ave_n>1:
                ave_depth = ave_depth // ave_n
                depth[r,c] = ave_depth
                i+=1
            c += 1
        r += 1
    # r = ROWS
    # while r>=0:
    #     c = COLS
    #     while c>=0:
    #         data = get_data(r, c, color, depth, conf)
    #         neigbors = get_neighbors(r, c, color, depth, conf)
    #         ave_depth = 0
    #         ave_n = 0
    #         for n in neigbors:
    #             diff_color = abs(int(n[0]) - data[0])
    #             if diff_color < ACR and n[2]>=data[2]:
    #                 ave_depth += n[1]
    #                 ave_n += 1
    #         if ave_n>0:
    #             ave_depth = ave_depth // ave_n
    #             depth[r,c] = ave_depth
    #             i+=1
    #         c -= 1
    #     r -= 1
    print(i, 'fixed')

# for i in range(5):
#     print(i+1, '...')
#     fix(r1, d1, c1)
fix(r1, d1, c1)

r1 = r1[1:50+KERNEL-2,1:80+KERNEL-2]
d1 = d1[1:50+KERNEL-2,1:80+KERNEL-2]
c1 = c1[1:50+KERNEL-2,1:80+KERNEL-2]

r1 = Image.fromarray(r0)
d1 = Image.fromarray(d1)
c1 = Image.fromarray(c1)

# _, axs = plt.subplots(2,3)
# axs[0,0].imshow(r1, cmap='gray')
# axs[0,1].imshow(d1, cmap='gray')
# axs[0,2].imshow(c1, cmap='gray')
# axs[1,0].imshow(d1, cmap='gray')
# axs[1,1].imshow(c1, cmap='gray')
# axs[1,2].imshow(r1, cmap='gray')
# plt.show()

r1.save('temp/sample/rgb.jpg')
d1.save('temp/sample/depth.png')
c1.save('temp/sample/conf.png')

rgb = Image.open('temp/sample/rgb.jpg')
depth = Image.open('temp/sample/depth.png')

rgb = o3d.io.read_image('temp/sample/rgb.jpg')
depth = o3d.io.read_image('temp/sample/depth.png')
rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, depth_trunc=1.5, convert_rgb_to_intensity=False)
# pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC)
# visualize([pcd])

volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=1.0/512.0,
                sdf_trunc=0.04,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
volume.integrate(rgbd, INTRINSIC, np.linalg.inv(np.identity(4)))
mesh = volume.extract_triangle_mesh()
mesh.compute_vertex_normals()
visualize([mesh])
# pcd = volume.extract_point_cloud()
# visualize([pcd])