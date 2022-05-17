import open3d as o3d
from modeler.z import *
from PIL import Image

# rgb = np.array(Image.open('temp/rgb/c00000.jpg'))
# depth = np.array(Image.open('temp/depth/d00000.png'))
# depth2 = np.array(Image.open('temp/fixed/depth.png'))
# print(rgb.shape, depth.shape, depth2.shape)

rgbd = load_rgbd('temp/rgb/c00000.jpg', 'temp/fixed/depth.png')
# rgbd = load_rgbd('temp/rgb/c00000.jpg', 'temp/depth/depth00000.png')
pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC)
visualize([pcd])