from PIL import Image
from matplotlib.colors import rgb2hex
import matplotlib.pyplot as plt
import numpy as np
import open3d as o3d
from modeler.z import *

rgb = Image.open("temp/images/rgb.jpg")
depth = Image.open("temp/images/depth.png")


rgb = rgb.resize((160,90))
rgb.save("temp/images/rgb-1.jpg")
rgb = np.array(rgb)
depth = np.array(depth)

'''
    1 2     
    3 4
'''

# rgb = np.rot90(np.rot90(np.rot90(rgb)))
# depth = np.rot90(np.rot90(np.rot90(depth)))

# fig, axs = plt.subplots(1,2)
# axs[0].imshow(rgb)
# axs[1].imshow(depth)
# plt.show()

# depth = Image.open("temp/images/depth.png")
# depth2 = Image.open("depth.png")
# print(depth.mode, depth2.mode)

# depth = np.array(depth)
# depth2 = np.array(depth2)
# print(depth.shape, depth2.shape)

# print(depth.dtype, depth2.dtype)

# trans = np.identity(4)

trans = np.array([
    [-1,0,0,0],
    [0,1,0,0],
    [0,0,-1,0],
    [0,0,0,1]
])
t = np.array([
    [0,1,0,0],
    [-1,0,0,0],
    [0,0,1,0],
    [0,0,0,1]
])
trans = np.dot(trans, t)
print(trans)

rgbd = load_rgbd("temp/images/rgb-1.jpg", "temp/images/depth.png")
pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC)
pcd.transform(trans)
o3d.visualization.draw_geometries([pcd])

# volume = o3d.pipelines.integration.ScalableTSDFVolume(
#                 voxel_length=4.0/512.0,
#                 sdf_trunc=0.04,
#                 color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)

# volume.integrate(rgbd, INTRINSIC, np.linalg.inv(trans))
# mesh = volume.extract_triangle_mesh()
# mesh.compute_vertex_normals()
# o3d.visualization.draw_geometries([mesh])