import sys
sys.path.append('C:/Users/ivand/Documents/Projects/Pigs/Blender-CV-Utils')

from blender_cv_utils.trackable import SceneObject
import time
import bpy
import numpy as np
import os
import pickle
import datetime
import matplotlib.pyplot as plt


obs = [SceneObject('Cube')]


class Renderer():
    def __init__(self, cameras, obs, output_path, output_suffix='default', blender_file_path=None):
        bpy.ops.wm.open_mainfile(filepath=blender_file_path)
        time.sleep(1)
        assert len(list(bpy.data.scenes)) == 1

        self.cameras = cameras
        self.obs = obs
        self.frame_index = 0

        time_suffix = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.output_path = os.path.join(output_path, f'{output_suffix}_{time_suffix}')
        os.mkdir(self.output_path)
        
        self.scene = bpy.data.scenes['Scene']
        self.resolution_percentage = self.scene.render.resolution_percentage
        self.resolution_x = self.scene.render.resolution_x
        self.resolution_y = self.scene.render.resolution_y
        self.pixel_aspect_x = self.scene.render.pixel_aspect_x
        self.pixel_aspect_y = self.scene.render.pixel_aspect_y
        self.engine = self.scene.render.engine

        # also save global params that is not change during generation

        pickle.dump({'resolution_percentage': self.resolution_percentage,
                        'resolution_x': self.resolution_x,
                        'resolution_y': self.resolution_y,
                        'pixel_aspect_x': self.pixel_aspect_x,
                        'pixel_aspect_y': self.pixel_aspect_y,
                        'engine': self.engine,}, 
                    open(os.path.join(self.output_path, 'render_params.pickle'), 'wb'))

        self._init_cryptomatte()

    def _init_cryptomatte(self):
        if not self.scene.use_nodes:
            self.scene.use_nodes = True
        else:
            print('Nodes initiated')
            return
        self.scene.view_layers["ViewLayer"].use_pass_cryptomatte_object = True

        node_tree = self.scene.node_tree
        node_tree.nodes.new("CompositorNodeCryptomatteV2")
        node_tree.nodes.new("CompositorNodeViewer")
        node_tree.links.new(node_tree.nodes['Cryptomatte'].outputs['Image'],
                            node_tree.nodes['Viewer'].inputs['Image'])
        node_tree.links.new(node_tree.nodes['Render Layers'].outputs['Image'],
                            node_tree.nodes['Cryptomatte'].inputs['Image'])
        self.scene.render.use_compositing = False

    def get_mask_for_object(self, ob):
        # bpy.ops.render.render(write_still=True)
        # self.scene.render.use_compositing = True # update nodes
        self.scene.node_tree.nodes['Cryptomatte'].matte_id = ob.name
        # self.scene.render.use_compositing = True # update nodes
        time.sleep(1)  # blender tackle
        pixels = bpy.data.images['Viewer Node'].pixels
        image = np.array(pixels).reshape(self.resolution_y,self.resolution_x,4)
        return image[::-1] # don't know why but this image is turned upside down
    
    def render(self, image_path, render_engine=None):
        if render_engine:
            self.scene.render.engine = render_engine

        self.scene.render.filepath = image_path
        bpy.ops.render.render(write_still=True)
        self.scene.render.engine = self.engine
        
    
    def get_xray_mask_for_object(self, path, ob):
        for o in self.obs:
            if o.type == "MESH":
                o.hide_render = True

        ob.hide_render = False
        self.render(path, render_engine='BLENDER_WORKBENCH')

        for o in self.obs:
            if o.type == "MESH":
                o.hide_render = False

    def main(self):
        annots = {ob.name:ob.get_annotations() for ob in self.obs}
        cameras = [ob for ob in self.obs if ob.type=='CAMERA']
        meshes = [ob for ob in self.obs if ob.type=='MESH']
        for camera in cameras:
            camera.make_active()
            impath = os.path.join(self.output_root_path, self.output_suffix, f'image_{camera.name}.png')
            self.render(image_path=impath)
            annots[camera.name]['image_path'] = impath

            for mesh in meshes: # получаем маски для объектов
                mask_path = os.path.join(self.output_root_path, self.output_suffix, f'image_{camera.name}_mask_{mesh.name}.png')
                mask = self.get_mask_for_object(mesh)
                plt.imsave(mask_path, mask)
                annots[mesh.name]['mask_path'] = mask_path

                # xray маска для объекта
                mask_path = os.path.join(self.output_root_path, self.output_suffix, f'image_{camera.name}_xraymask_{mesh.name}.png')
                self.get_xray_mask_for_object(mask_path, mesh)
                annots[mesh.name]['xraymask_path'] = mask_path


        pickle.dump(annots, open(os.path.join(self.output_root_path, self.output_suffix, f'annots_{self.frame_index}.pickle'), 'wb'))
        self.frame_index+=1