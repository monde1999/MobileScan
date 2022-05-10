import open3d as o3d
import numpy as np
import time
import copy
from threading import Thread

MAX_THREAD = 4
FRAMES_PER_FRAGMENT = 100

INTRINSIC = o3d.camera.PinholeCameraIntrinsic(width=640, height=480, fx=525, fy=525, cx=319.5, cy=239.5)
ODO_OPTION = o3d.pipelines.odometry.OdometryOption()

class Counter:
    processes = 0

def save_pcd(fn, pcd):
    o3d.io.write_point_cloud(fn, pcd, write_ascii=False, compressed=True, print_progress=False)

def load_pcd(fn):
    return o3d.io.read_point_cloud(fn)

def visualize(geometries):
    o3d.visualization.draw_geometries(geometries,
                                    zoom=0.48,
                                    front=[0.0999, -0.1787, -0.9788],
                                    lookat=[0.0345, -0.0937, 1.8033],
                                    up=[-0.0067, -0.9838, 0.1790])

def integrate(rgbds_odo, pose_graph):
    volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=4.0/512.0,
                sdf_trunc=0.04,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    i = 0
    for node in pose_graph.nodes:
        rgb, depth = rgbds_odo[i][3]
        rgbd = load_rgbd(rgb, depth)
        volume.integrate(rgbd, INTRINSIC, np.linalg.inv(node.pose))
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
            elif source_id%5==0 and target_id%5==0:
                rgb, depth = rgbds_odo[target_id][3]
                target_rgbd = load_rgbd(rgb, depth)
                success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                                        source_rgbd, target_rgbd, INTRINSIC, np.identity(4),
                                        o3d.pipelines.odometry.RGBDOdometryJacobianFromColorTerm(),
                                        ODO_OPTION)
                pose_graph.edges.append(o3d.pipelines.registration.PoseGraphEdge(source_id,
                                                                                target_id,
                                                                                trans,
                                                                                info,
                                                                                uncertain=True))
    method = o3d.pipelines.registration.GlobalOptimizationLevenbergMarquardt()
    criteria = o3d.pipelines.registration.GlobalOptimizationConvergenceCriteria()
    option = o3d.pipelines.registration.GlobalOptimizationOption(
            max_correspondence_distance=0.05,
            edge_prune_threshold=0.25,
            preference_loop_closure=0.25,
            reference_node=0)
    # o3d.pipelines.registration.global_optimization(pose_graph, method, criteria, option)
    return pose_graph


def load_batch_odo(rgbds_odo, source_rgbd, target_rgbd, target_rgb, target_depth, index, loaded):
    while loaded.processes>=MAX_THREAD:
        print('loaded: %d' % loaded.processes)
        time.sleep(1.0)
    loaded.processes += 1
    success, trans, info = o3d.pipelines.odometry.compute_rgbd_odometry(
                    source_rgbd, target_rgbd, INTRINSIC, np.identity(4),
                    o3d.pipelines.odometry.RGBDOdometryJacobianFromColorTerm(),
                    ODO_OPTION)
    if success:
        rgb_d = (target_rgb, target_depth)
        rgbds_odo[index] = (success, trans, info, rgb_d)
    print("INFO: %d integrated" % index)
    loaded.processes -= 1

def load_rgbd(rgb, depth):
    rgb = o3d.io.read_image(rgb)
    depth = o3d.io.read_image(depth)
    return o3d.geometry.RGBDImage.create_from_color_and_depth(rgb, depth, depth_trunc=4.0, convert_rgb_to_intensity=False)