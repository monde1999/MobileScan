import glob
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from modeler.z import *
import open3d as o3d

rgbs = glob.glob('dataset2/rgb/*.jpg')
depths = glob.glob('dataset2/depth/*.png')
confs = glob.glob('dataset2/depth/*.png')

rgbs.sort()
depths.sort()
confs.sort()

print(len(rgbs), len(depths), len(confs))

max = 10
rgbs = rgbs[:max]
depths = depths[:max]
confs = confs[:max]

rgbds = []
fn = 1

for rgb, depth, conf in zip(rgbs, depths, confs):
    rgb = Image.open(rgb)
    depth = Image.open(depth)
    conf = Image.open(conf)

    rgb = np.asarray(rgb)
    rgb1 = (rgb[:, :, 0] + rgb[:, :, 1] + rgb[:, :, 2]) // 3  # grayscale
    depth = np.asarray(depth)
    conf = np.asarray(conf)

    # rgb1, depth, conf = fix(rgb1, depth, conf)
    fn_rgb, fn_depth, fn_conf = save_images(rgb, depth, conf, fn)
    fn += 1

    rgbd = load_rgbd(fn_rgb, fn_depth)
    rgbds.append(rgbd)
    # pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC)
    # pcd.estimate_normals()
    # pcds.append(pcd)

    # _, axs = plt.subplots(1,3)
    # axs[0].imshow(rgb)
    # axs[1].imshow(depth)
    # axs[2].imshow(conf)
    # plt.show()

print(ODO_OPTION)

volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=1.0/512.0,
                sdf_trunc=0.04,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)

print('integrating 1...')
rgbd0 = rgbds.pop(0)
odometry = np.identity(4)
volume.integrate(rgbd0, INTRINSIC, np.linalg.inv(odometry))

count = 2
for rgbd in rgbds:
    print('integrating %d...' % count)
    count += 1

    success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                    rgbd0, rgbd, INTRINSIC, np.identity(4),
                    o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                    ODO_OPTION)
    
    odometry = np.dot(odometry, trans)
    volume.integrate(rgbd, INTRINSIC, np.linalg.inv(odometry))
    rgbd0 = rgbd

print('creating mesh...')
# mesh = volume.extract_triangle_mesh()
# mesh.compute_vertex_normals()
# visualize([mesh])
pcd = volume.extract_point_cloud()
visualize([pcd])

