from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Modeler

import numpy as np
import matplotlib.pyplot as plt

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
    # print(1, request.content_type)
    # print(3, request.data)
    # print(4, request.FILES)
    stream_body = request.stream.body
    # print(stream_body)
    stream_body = np.frombuffer(stream_body, dtype=np.uint16)
    stream_body = stream_body.reshape(160,90)
    print(stream_body)
    plt.imshow(stream_body, cmap="gray")
    plt.show()
    print(stream_body.shape)
    return Response("ok", status=status.HTTP_200_OK)