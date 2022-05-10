import open3d as o3d
import numpy as np
import time
import copy
from threading import Thread

MAX_THREAD = 4

INTRINSIC = o3d.camera.PinholeCameraIntrinsic(width=640, height=480, fx=525, fy=525, cx=319.5, cy=239.5)
ODO_OPTION = o3d.pipelines.odometry.OdometryOption()

class Fragment:
    def __init__(self, pcd_file, pose0):
        self.pcd_file = pcd_file
        self.pose0 = pose0

class Counter:
    processes = 0

class Node:
    def __init__(self, value, next):
        self.value = value
        self.next = next

class SinglyList:
    first = None
    last = None
    size = 0
    def append(self, value):
        node = Node(value, None)
        if self.first==None: 
            self.first = node
        else: 
            self.last.next = node
        self.last = node
        self.size += 1

def load_batch_odo(rgbds_odo, source_rgbd, target_rgbd, target_rgb, target_depth, index, loaded):
    while loaded.processes>=MAX_THREAD:
        time.sleep(1)
    success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                    source_rgbd, target_rgbd, INTRINSIC, np.identity(),
                    o3d.pipelines.odometry.RGBDOdometryJacobianFromColorTerm(),
                    ODO_OPTION)
    if success:
        rgbd = (target_rgb, target_depth)
        rgbds_odo[index] = (success, trans, info, rgbd)
    loaded.processes -= 1

def load_rgbd(rgb, depth):
    rgb = o3d.io.read_image(rgb)
    depth = o3d.io.read_image(depth)
    return o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, depth_trunc=4.0, convert_rgb_to_intensity=False)

def get_odometry(source_rgbd, target_rgbd, trans_init):
    return o3d.pipelines.odometry.compute_rgbd_odometry(
                    source_rgbd, target_rgbd, INTRINSIC, np.identity(),
                    o3d.pipelines.odometry.RGBDOdometryJacobianFromColorTerm(),
                    ODO_OPTION)

def get_optimized_pose_graph(rgbds_and_odo:SinglyList, is_rgbd):
    pose_graph = o3d.pipelines.registration.PoseGraph()

    node = rgbds_and_odo.first
    odometry = node.value[1]
    pose_graph.nodes.append(o3d.pipelines.registration.PoseGraphNode(np.linalg.inv(odometry)))

    loaded = Counter()

    source_id = 0
    source = node
    while source!=None:
        print('adding pose in posegraph %d/%d...' % (source_id+1, rgbds_and_odo.size))
        target_id = source_id + 1
        target = source.next
        if target==None: break
        odometry = target.value[1]
        info = target.value[2]
        trans = target.value[3]
        pose_graph.nodes.append(
            o3d.pipelines.registration.PoseGraphNode(
                np.linalg.inv(odometry)))
        pose_graph.edges.append(
            o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                        target_id,
                                                        trans,
                                                        info,
                                                        uncertain=False))

        while loaded.processes>4:
            time.sleep(1)
        if source_id%5==0:
            loaded.processes += 1
            thread = Thread(target=odo_uncertain, args=(pose_graph, source, target, source_id, target_id, is_rgbd, loaded))
            thread.daemon = True
            thread.start()
        
        source = source.next
        source_id += 1
    print('waiting for adding pose in posegraph...')
    while loaded.processes>0:
        time.sleep(1)

    method = o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt()
    criteria = o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria()
    option = o3d.pipelines.registration.GlobalOptimizationOption(
        max_correspondence_distance=0.05,
        edge_prune_threshold=0.25,
        preference_loop_closure=0.25,
        reference_node=0)
    o3d.pipelines.registration.global_optimization(pose_graph, method, criteria, option)
    return pose_graph

def pcd_integrate(pcds_and_odo:SinglyList, pose_graph):
    obj = o3d.geometry.PointCloud()
    count = 1
    node = pcds_and_odo.first
    for node1 in pose_graph.nodes:
        print('integrating %d/%d...' % (count, pcds_and_odo.size))
        pcd = node.value[0]
        pcd.transform(np.linalg.inv(node1.pose))
        obj += pcd
        obj = obj.voxel_down_sample(0.01)
        node = node.next
        count += 1
    return obj

def rgbd_integrate(rgbds_and_odo:SinglyList, pose_graph):
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=4.0/512.0,
                sdf_trunc=0.04,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    count = 1
    node = rgbds_and_odo.first
    for node1 in pose_graph.nodes:
        print('integrating %d/%d...' % (count, rgbds_and_odo.size))
        rgb, depth = node.value[0]
        rgbd = load_rgbd(rgb, depth)
        node = node.next
        volume.integrate(rgbd, INTRINSIC, np.linalg.inv(node1.pose))
        count += 1
    return volume.extract_point_cloud()

def odo_uncertain(pose_graph, source, target, source_id, target_id, is_rgbd, loaded):
    target_id += 1
    target = target.next
    # if target!=None: trans_init = target.value[3]
    count = 0
    if is_rgbd:
        rgb, depth = source.value[0]
        source_rgbd = load_rgbd(rgb, depth)
        while target!=None:
            # if count == 3: break
            if (target_id+1)%5==0:
            # if True:
                # print('sourceid%d targetid%d' % (source_id,target_id))
                rgb, depth = target.value[0]
                target_rgbd = load_rgbd(rgb, depth)
                # target_trans = target.value[3]
                # trans_init = np.dot(target_trans, trans_init)
                trans_init = np.identity(4)
                success, trans, info = get_odometry(source_rgbd, target_rgbd, trans_init)
                pose_graph.edges.append(
                    o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                            target_id,
                                                            trans,
                                                            info,
                                                            uncertain=True))
            count += 1
            target_id += 1
            target = target.next
    else:
        source_pcd = source.value[0]
        while target!=None:
            # if count == 3: break
            if (target_id+1)%5==0:
            # if True:
                # print('sourceid%d targetid%d' % (source_id,target_id))
                target_pcd = target.value[0]
                # target_trans = target.value[3]
                # trans_init = np.dot(target_trans, trans_init)
                # trans_init = np.identity(4)
                success, trans, info = estimate(source_pcd, target_pcd)
                pose_graph.edges.append(
                    o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                            target_id,
                                                            trans,
                                                            info,
                                                            uncertain=True))
            count += 1
            target_id += 1
            target = target.next
    loaded.processes -= 1

def visualize(geometries):
    o3d.visualization.draw_geometries(geometries,
                                    zoom=0.48,
                                    front=[0.0999, -0.1787, -0.9788],
                                    lookat=[0.0345, -0.0937, 1.8033],
                                    up=[-0.0067, -0.9838, 0.1790])

def draw_registration_result(source, target, transformation):
    source_temp = copy.deepcopy(source)
    target_temp = copy.deepcopy(target)
    source_temp.paint_uniform_color([1, 0.706, 0]) # yellow
    # target_temp.paint_uniform_color([0, 0.651, 0.929]) # blue
    source_temp.transform(transformation)
    o3d.visualization.draw_geometries([source_temp, target_temp],
                                    zoom=0.48,
                                    front=[0.0999, -0.1787, -0.9788],
                                    lookat=[0.0345, -0.0937, 1.8033],
                                    up=[-0.0067, -0.9838, 0.1790])

def save_pcd(fn, pcd):
    o3d.io.write_point_cloud(fn, pcd, write_ascii=False, compressed=True, print_progress=False)

def load_pcd(fn):
    return o3d.io.read_point_cloud(fn)

def save_odo(fn, s_list:SinglyList):
    odos = []
    node = s_list.first
    while node!=None:
        odometry = node.value[1]
        info = node.value[2]
        odos.append([odometry, info])
        node = node.next
    odos = np.array(odos, dtype=object)
    np.save(fn,odos)

def load_odo(fn):
    return np.load(fn, allow_pickle=True)

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
    threshold = 0.05

    s_down, s_fpfh = preprocess_point_cloud(source, voxel_size)
    t_down, t_fpfh = preprocess_point_cloud(target, voxel_size)
    # result_ransac = execute_global_registration(
    #                 source_down, target_down, s_fpfh, t_fpfh, 0.05)
    result = o3d.pipelines.registration.registration_fast_based_on_feature_matching(
            s_down, t_down, s_fpfh, t_fpfh,
            o3d.pipelines.registration.FastGlobalRegistrationOption(
                maximum_correspondence_distance=distance_threshold))
    trans_init = result.transformation
    # trans_init = np.identity(4)
    result_icp = o3d.pipelines.registration.registration_icp(
        s_down, t_down, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    # result_icp = o3d.pipelines.registration.registration_colored_icp(
    #         source, target, distance_threshold, trans_init
    #         )
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
        s_down, t_down, threshold, result_icp.transformation)
    # print(result_icp)
    return success, result_icp.transformation, info