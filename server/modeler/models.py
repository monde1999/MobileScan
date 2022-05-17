from .z import *
from threading import Thread
import time
import numpy as np

# loaded = Counter()

# def t1():
#     while True:
#         print('loaded: %d' % loaded.processes)
#         time.sleep(1)
# Thread(target=t1, daemon=True).start()

class FragmentGenerator:
    rgbds_odo = {}
    rgbd0 = None
    count = 0

    def add(self, rgb, depth, loaded:Counter):
        while loaded.processes>=MAX_THREAD:
            print('loaded: %d' % loaded.processes)
            time.sleep(1.0)
        loaded.processes += 1
        rgbd = load_rgbd(rgb, depth)
        if self.rgbd0==None:
            rgb_d = (rgb, depth)
            rgbd_odo = (True, np.identity(4), None, rgb_d)
            self.rgbds_odo[self.count] = rgbd_odo
        else:
            while self.rgbd0==None: time.sleep(0.1)
            Thread(target=load_batch_odo,
                args=(self.rgbds_odo, self.rgbd0, rgbd, rgb, depth, self.count, loaded),
                daemon=True
            ).start()
        self.rgbd0 = rgbd
        self.count += 1
        loaded.processes -= 1

    def generate_model(self, fn, loaded:Counter):
        print('generating fragment...')
        while loaded.processes!=0:
            print('loaded: %d' % loaded.processes)
            time.sleep(1.0)
        loaded.processes += 1
        fn = 'temp/fragment000/fragment%03d.pcd' % fn
        self.__integrate_and_save(self.rgbds_odo, fn)
        loaded.processes -= 1
        return fn

    def __integrate_and_save(self, rgbds_odo, fn):
        pose_graph = get_optimized_posegraph(rgbds_odo)
        pcd = integrate(rgbds_odo, pose_graph)
        save_pcd(fn, pcd)
        print('INFO: %s generated' % fn)


class Modeler:
    fragments = {}
    pcd = None
    mesh = None

    fg = FragmentGenerator()
    # fg_count = 0
    count = 0
    fn = 1

    loaded = Counter()

    def add(self, rgb, depth):
        self.fg.add(rgb, depth, self.loaded)
        self.count += 1
        if self.count>=FRAMES_PER_FRAGMENT: 
            # Thread(target=self.__generate_model, 
            #         args=(self.fg,self.fn,self.fn-1,self.loaded), 
            #         daemon=True
            # ).start()
            self.__generate_model(self.fg,self.fn,self.fn-1,self.loaded)
            self.fg = FragmentGenerator()
            self.count = 0
            self.fn += 1
            self.loaded = Counter()

    
    def __generate_model(self, fg:FragmentGenerator, fn:int, index:int, loaded:Counter):
        fn = self.fg.generate_model(fn, loaded)
        self.fragments[index] = fn

    def finalize(self):
        if self.count!=0:
            self.__generate_model(self.fg, self.fn, self.fn-1, self.loaded)

    

    

