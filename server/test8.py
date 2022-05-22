import glob
import numpy as np
from modeler.z import *
import open3d as o3d

pcds = glob.glob('frags/fragment*.pcd')
pcds.sort()
pcds = pcds[5:11]
frags = []
transs = []

for pcd in pcds:
    pcd = load_pcd(pcd)
    frags.append(pcd)
    
frag0 = frags.pop(0) 
frag01 = frag0

for frag in frags:
    success, trans, info = estimate(frag0, frag)
    transs.append(trans)
    frag0 = frag
 
voxel_size = 0.001
frag0 = frag01
frag0 = frag0.voxel_down_sample(voxel_size)
trans0 = np.identity(4)
pcds = []
    
for frag, trans in zip(frags, transs):
    trans0 = np.dot(trans0, trans)
    frag = frag.voxel_down_sample(voxel_size)
    frag.transform(trans0)
    #frag0 += frag
    #frag0 = frag0.voxel_down_sample(voxel_size)
    pcds.append(frag)

pcd0 = frag0
for pcd in pcds:
    pcd0 += pcd
pcd0 = pcd0.voxel_down_sample(voxel_size)
visualize([pcd0])
    