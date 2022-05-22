from modeler.z import load_pcd, visualize

pcd = load_pcd('temp/fragment000/fragment001.pcd')
# pcd = load_pcd('temp/fragment000/100frames_smoothen.pcd')
#pcd = load_pcd('frags/100frames_raw.pcd')
visualize([pcd])