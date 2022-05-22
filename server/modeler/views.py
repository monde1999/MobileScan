from ctypes import resize
from threading import Thread
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Modeler

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cv2
import time
from .z import *
import open3d as o3d

modeler = Modeler()
trans = np.array([
    [-1,0,0,0],
    [-1,1,0,0],
    [0,0,-1,0],
    [0,0,0,1]
])

# class Data:
    # frame = None
        
# def vis(data:Data):
#     while data.frame is None:
#         time.sleep(1.0)
#     while True:
#         cv2.imshow('Frame', data.frame)
#         if cv2.waitKey(25) & 0xFF == ord('q'):
#             break
#     cv2.destroyAllWindows()
# Thread(target=vis, args=(data,), daemon=True).start()


@api_view(['POST', 'GET'])
def integrate(request):
    if request.method=='GET':
        return Response('ok')
    fn = request.data.get('fn', None)
    rgb = request.FILES.get('rgb', None)
    depth = request.FILES.get('depth', None)
    conf = request.FILES.get('conf', None)
    if fn and rgb and depth and conf:
        fn = int(fn)
        f_rgb = default_storage.save('temp/rgb/c%05d.jpg' % fn, ContentFile(rgb.read()))
        f_depth = default_storage.save('temp/depth/d%05d.png' % fn, ContentFile(depth.read()))
        f_conf = default_storage.save('temp/conf/c%05d.png' % fn, ContentFile(conf.read()))

        # rgb = Image.open(f_rgb)
        # rgb = rgb.resize((160, 90))
        # rgb = rgb.crop((40,20,120,70))
        # rgb = np.asarray(rgb)
        # rgb = (rgb[:, :, 0] + rgb[:, :, 1] + rgb[:, :, 2]) // 3  # grayscale

        # depth = Image.open(f_depth)
        # depth = np.asarray(depth)
        # depth = np.fromfile(f_depth, dtype=np.uint16)
        # depth = np.asarray(depth)
        # depth = np.reshape(depth, (50,80))

        # conf = Image.open(f_conf)
        # conf = np.asarray(conf)
        # conf = np.fromfile(f_conf, dtype=np.uint8)
        # conf = np.asarray(conf)
        # conf = np.reshape(conf, (50,80))

        # rgb, depth, conf = fix(rgb, depth, conf)
        # depth = Image.fromarray(depth)
        # depth.save(f_depth)

        modeler.add(f_rgb, f_depth)
    return Response(status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
def go(request):
    modeler.finalize()
    return Response(status=status.HTTP_200_OK)

@api_view(['POST'])
def view(request:Request):
    fn = request.data.get('fn', None)
    rgb = request.FILES.get('rgb', None)
    depth = request.FILES.get('depth', None)
    conf = request.FILES.get('conf', None)
    if fn and rgb and depth:
        fn = int(fn)
        f_rgb = default_storage.save('temp/rgb/c%05d.jpg' % fn, ContentFile(rgb.read()))
        f_depth = default_storage.save('temp/depth/d%05d.png' % fn, ContentFile(depth.read()))
        f_conf = default_storage.save('temp/conf/c%05d.png' % fn, ContentFile(conf.read()))

        rgb = Image.open(f_rgb)
        rgb = rgb.resize((160, 90))
        rgb2 = rgb.crop((40,20,120,70))
        rgb2.save(f_rgb)

        depth = np.fromfile(f_depth, dtype=np.uint16)
        depth = np.reshape(depth, (50,80))
        depth2 = Image.fromarray(depth)
        depth2.save(f_depth)

        conf = np.fromfile(f_conf, dtype=np.uint8)
        conf = np.reshape(conf, (50,80))
        conf2 = Image.fromarray(conf)
        conf2.save(f_conf)
        
        print('%s added' % f_rgb)

        # _, axs = plt.subplots(1,3)
        # axs[0].imshow(rgb)
        # axs[1].imshow(depth)
        # axs[2].imshow(conf)
        # plt.show()

        # rgbd = load_rgbd(f_rgb, f_depth)
        # pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC)
        # pcd.transform(trans)
        # o3d.visualization.draw_geometries([pcd])

        # volume = o3d.pipelines.integration.ScalableTSDFVolume(
        #         voxel_length=4.0/512.0,
        #         sdf_trunc=0.04,
        #         color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
        # volume.integrate(rgbd, INTRINSIC, np.linalg.inv(trans))
        # mesh = volume.extract_triangle_mesh()
        # mesh.compute_vertex_normals()
        # o3d.visualization.draw_geometries([mesh])

        # depth2 = Image.fromarray(depth)
        # depth2 = depth2.rotate(-90)
        # depth2 = depth2.resize((640,480))
        # depth2 = np.array(depth2)
        # data.frame = depth2
    return Response("ok", status=status.HTTP_200_OK)