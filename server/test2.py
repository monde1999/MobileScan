from PIL import Image
from matplotlib.colors import rgb2hex
import matplotlib.pyplot as plt
import numpy as np
import open3d as o3d
from modeler.z import *
import glob
from modeler.models import *

# rgb = Image.open("temp/rgb/r00001.jpg")
# depth = Image.open("temp/depth/d00001.png")
# rgb = np.array(rgb)
# depth = np.array(depth)

rgbs = glob.glob('temp/rgb/*.jpg')
depths = glob.glob('temp/depth/*.png')
rgbs.sort()
depths.sort()

last = 10
rgbs = rgbs[:last]
depths = depths[:last]

def show_image(rgb, depth):
    rgb = Image.open(rgb)
    depth = Image.open(depth)
    _, axs = plt.subplots(1,2)
    axs[0].imshow(rgb)
    axs[1].imshow(depth)
    plt.show()

odometry = np.array([
    [-1,0,0,0],
    [-1,1,0,0],
    [0,0,-1,0],
    [0,0,0,1]
])

modeler = FragmentGenerator()
loaded = Counter()


for rgb, depth in zip(rgbs, depths):
    rgbd = load_rgbd(rgb, depth)
    pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, INTRINSIC, )
    visualize([pcd])
    # modeler.add(rgb, depth, loaded)
# modeler.generate_model(1, loaded)