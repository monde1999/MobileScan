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

modeler = Modeler()

@api_view(['POST', 'GET'])
def integrate(request):
    if request.method=='GET':
        return Response('ok')
    rgb = request.data['rgb']
    rgb = default_storage.save('temp/images/rgb.jpg', ContentFile(rgb.read()))
    depth = request.data['depth']
    depth = default_storage.save('temp/images/depth.png', ContentFile(depth.read()))
    modeler.add(rgb, depth)
    return Response(status=status.HTTP_202_ACCEPTED)

@api_view(['GET'])
def go(request):
    modeler.finalize()
    return Response(status=status.HTTP_200_OK)

@api_view(['POST'])
def view(request:Request):
    rgb = request.FILES.get('rgb', None)
    depth = request.FILES.get('depth', None)
    if rgb and depth:
        f_rgb = default_storage.save('temp/images/rgb.jpg', ContentFile(rgb.read()))
        f_depth = default_storage.save('temp/images/depth.png', ContentFile(depth.read()))

        rgb = Image.open(f_rgb)
        depth = np.fromfile(f_depth, dtype=np.uint16)
        depth = np.reshape(depth, (90,160))
        depth2 = Image.fromarray(depth)
        depth2.save(f_depth)

        fig, axs = plt.subplots(1,2)
        axs[0].imshow(rgb)
        axs[1].imshow(depth)
        plt.show()
    return Response("ok", status=status.HTTP_200_OK)