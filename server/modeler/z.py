from matplotlib import widgets
import open3d as o3d
import numpy as np
import time
import copy
from threading import Thread
from PIL import Image

MAX_THREAD = 4
FRAMES_PER_FRAGMENT = 200
KERNEL = 3
ACR = 5  # acceptable color range
ROWS = 50 #height
COLS = 80 #width
MAX_DEPTH = 1.1

# 0,0,160,90 --> 0,60,640,420
INTRINSIC = o3d.camera.PinholeCameraIntrinsic(width=COLS, height=ROWS, fx=116.36878, fy=116.38366, cx=81.337074-COLS/2, cy=46.473267-ROWS/2)
# INTRINSIC = o3d.camera.PinholeCameraIntrinsics(width=160, height=90, fx=116.36878, fy=116.38366, cx=81.337074, cy=46.473267)
ODO_OPTION = o3d.pipelines.odometry.OdometryOption()
ODO_OPTION.max_depth_diff = 0.5
ODO_OPTION.max_depth = MAX_DEPTH


class Counter:
    processes = 0

def save_pcd(fn, pcd):
    o3d.io.write_point_cloud(fn, pcd, write_ascii=False, compressed=True, print_progress=False)

def load_pcd(fn):
    return o3d.io.read_point_cloud(fn)

def visualize(geometries):
    geo_copies = []
    # trans = np.array([
    #     [-1,0,0,0],
    #     [-1,1,0,0],
    #     [0,0,-1,0],
    #     [0,0,0,1]
    # ])
    trans = np.array([
        [0,-2,0,0],
        [-2,0,0,0],
        [0,0,-1,0],
        [0,0,0,1]
    ])
    for g in geometries:
        c = copy.deepcopy(g)
        c.transform(trans)
        geo_copies.append(c)
    o3d.visualization.draw_geometries(geo_copies)
    
def preprocess_point_cloud(pcd, voxel_size):
    pcd_down = pcd.voxel_down_sample(voxel_size)

    radius_normal = voxel_size * 2
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))

    radius_feature = voxel_size * 5
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100))
    return pcd_down, pcd_fpfh

def execute_global_registration(source_down, target_down, source_fpfh,
                                target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        3, [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(
                0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                distance_threshold)
        ], o3d.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999))
    return result
    
def estimate(source, target):
    voxel_size = 0.05
    distance_threshold = voxel_size * 1.4
    voxel_size2 = 0.01
    distance_threshold2 = voxel_size * 1.4
    #threshold = 0.05

    s_down, s_fpfh = preprocess_point_cloud(source, voxel_size)
    t_down, t_fpfh = preprocess_point_cloud(target, voxel_size)
    result_ransac = execute_global_registration(
                    s_down, t_down, s_fpfh, t_fpfh, voxel_size)
    #result = o3d.pipelines.registration.registration_fast_based_on_feature_matching(
    #        s_down, t_down, s_fpfh, t_fpfh,
    #        o3d.pipelines.registration.FastGlobalRegistrationOption(
    #            maximum_correspondence_distance=distance_threshold))
    print(result_ransac)
    trans_init = result_ransac.transformation
    #trans_init = np.identity(4)
    
    s_down = source.voxel_down_sample(voxel_size2)
    t_down = source.voxel_down_sample(voxel_size2)
    
    #result_icp = o3d.pipelines.registration.registration_icp(
    #    s_down, t_down, distance_threshold2, trans_init,
    #    o3d.pipelines.registration.TransformationEstimationPointToPlane())
    result_icp = o3d.pipelines.registration.registration_colored_icp(
            s_down, t_down, distance_threshold2, trans_init
            )
    success = result_icp.fitness > 0.8 # and result_icp.inlier_rmse < 0.02
    # success = result_icp.inlier_rmse < 0.02
    # success = True
    # if success and result_icp.fitness!=1.0:
    #     result_icp = o3d.pipelines.registration.registration_colored_icp(
    #         source, target, threshold2, result_icp.transformation
    #         )
    #     success = result_icp.fitness > 0.9
    # o3d.pipelines.registration.
    info = o3d.pipelines.registration.get_information_matrix_from_point_clouds(
        s_down, t_down, distance_threshold2, result_icp.transformation)
    print(result_icp)
    return success, result_icp.transformation, info

def integrate(rgbds_odo, pose_graph):
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=1.0/512.0,
                sdf_trunc=0.04,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    i = 0
    for node in pose_graph.nodes:
        print('integrating %d...' % (i+1))
        rgb, depth = rgbds_odo[i][3]
        rgbd = load_rgbd(rgb, depth)
        volume.integrate(rgbd, INTRINSIC, np.linalg.inv(node.pose))
        # visualize([volume.extract_point_cloud()])
        i += 1
    return volume.extract_point_cloud()


def get_optimized_posegraph(rgbds_odo:dict):
    pose_graph = o3d.pipelines.registration.PoseGraph()
    odometry = np.identity(4)
    pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(np.linalg.inv(odometry)))
    end = len(rgbds_odo)
    for source_id in range(0, end-1):
        print("INFO: posing odo%d" % source_id)
        rgb, depth = rgbds_odo[source_id][3]
        source_rgbd = load_rgbd(rgb, depth)
        for target_id in range(source_id+1, end):
            if target_id==source_id+1:
                trans, info = rgbds_odo[target_id][1:3]
                odometry = np.dot(trans, odometry)
                pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(np.linalg.inv(odometry)))
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                                                target_id,
                                                                                trans,
                                                                                info,
                                                                                uncertain=False))
            elif target_id-source_id<10: # and source_id%5==0 and target_id%5==0:
                rgb, depth = rgbds_odo[target_id][3]
                target_rgbd = load_rgbd(rgb, depth)
                success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                                        source_rgbd, target_rgbd, INTRINSIC, np.identity(4),
                                        o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                                        ODO_OPTION)
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                                                target_id,
                                                                                trans,
                                                                                info,
                                                                                uncertain=True))
            else: break
    method = o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt()
    criteria = o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria()
    option = o3d.pipelines.registration.GlobalOptimizationOption(
            max_correspondence_distance=0.002,
            edge_prune_threshold=0.25,
            preference_loop_closure=0.25,
            reference_node=0)
    o3d.pipelines.registration.global_optimization(pose_graph, method, criteria, option)
    return pose_graph


def load_batch_odo(rgbds_odo, source_rgbd, target_rgbd, target_rgb, target_depth, index, loaded):
    print('INFO: adding %d...' % index)
    while loaded.processes>=MAX_THREAD:
        print('loaded: %d' % loaded.processes)
        time.sleep(1.0)
    loaded.processes += 1
    success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                    source_rgbd, target_rgbd, INTRINSIC, np.identity(4),
                    o3d.pipelines.odometry.RGBDOdometryJacobianFromHybridTerm(),
                    ODO_OPTION)
    if success:
        rgb_d = (target_rgb, target_depth)
        rgbds_odo[index] = (success, trans, info, rgb_d)
    loaded.processes -= 1

def load_rgbd(rgb, depth):
    rgb = o3d.io.read_image(rgb)
    depth = o3d.io.read_image(depth)
    return o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, depth_trunc=MAX_DEPTH, convert_rgb_to_intensity=False)

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

def save_images(color, depth, conf, fn):
    color = Image.fromarray(color)
    depth = Image.fromarray(depth)
    conf = Image.fromarray(conf)
    fn_rgb = 'temp/sample/r%05d.jpg' % fn
    fn_depth = 'temp/sample/d%05d.png' % fn
    fn_conf = 'temp/sample/c%05d.png' % fn
    color.save(fn_rgb)
    depth.save(fn_depth)
    conf.save(fn_conf)
    return (fn_rgb, fn_depth, fn_conf)

def fix(color, depth, conf):
    color = np.pad(color, KERNEL-2, mode='constant')
    depth = np.pad(depth, KERNEL-2, mode='constant')
    conf = np.pad(conf, KERNEL-2, mode='constant')

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
    # print(i, 'fixed')

    color = color[1:50+KERNEL-2,1:80+KERNEL-2]
    depth = depth[1:50+KERNEL-2,1:80+KERNEL-2]
    conf = conf[1:50+KERNEL-2,1:80+KERNEL-2]

    return (color, depth, conf)