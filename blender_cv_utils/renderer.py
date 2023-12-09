import bpy
import os
import json

class RenderHandler:

    def __init__(self, output_path, output_suffix, cameras, objects):

        self.output_path = output_path
        self.output_suffix = output_suffix
        self.cameras = cameras
        self.objects = objects

        self.is_nodes_created = False

        self.initCryptomatte()

        if not os.path.isdir(os.path.join(self.output_path, self.output_suffix)):
            os.mkdir(os.path.join(self.output_path, self.output_suffix))

        scene = bpy.context.scene

        self.global_params = {'resolution_percentage': scene.render.resolution_percentage,
                              'resolution_x': scene.render.resolution_x,
                              'resolution_y': scene.render.resolution_y,
                              'pixel_aspect_x': scene.render.pixel_aspect_x,
                              'pixel_aspect_y': scene.render.pixel_aspect_y,
                              'engine': scene.render.engine,}
        json.dump(self.global_params, open(os.path.join(output_path, output_suffix, f'global_params.json'),'w'), indent=4)



    def initCryptomatte(self):
        # initiate cryptomatte
        if not self.is_nodes_created:
            scene = bpy.context.scene
            if not scene.use_nodes:
                scene.use_nodes = True
            scene.render.use_compositing = True
            scene.view_layers["ViewLayer"].use_pass_cryptomatte_object = True
            
            output_nodes=[]
            for ob in self.objects:
                if ob.type!='MESH' or not ob.is_mask:
                    continue
                output_node = scene.node_tree.nodes.new("CompositorNodeOutputFile")
                output_node.base_path = os.path.join(self.output_path, self.output_suffix, ob.name)
                output_node.name = ob.name
                output_nodes.append(output_node)
                cryptomatte = scene.node_tree.nodes.new("CompositorNodeCryptomatteV2")
                cryptomatte.matte_id = ob.name
                scene.node_tree.links.new(cryptomatte.outputs['Image'], output_node.inputs['Image'])
                scene.node_tree.links.new(cryptomatte.inputs['Image'], scene.node_tree.nodes['Render Layers'].outputs['Image'])
            
            
            output_node = scene.node_tree.nodes.new("CompositorNodeOutputFile")
            output_node.base_path = os.path.join(self.output_path, self.output_suffix)
            scene.node_tree.links.new(scene.node_tree.nodes['Render Layers'].outputs['Image'], output_node.inputs['Image'])     
            self.is_nodes_created = True

    def render_frame(self, frame_index):
        scene = bpy.context.scene
        depsgraph = bpy.context.evaluated_depsgraph_get()
        annots = {ob.name:ob.get_annotations(depsgraph, cameras=self.cameras) for ob in self.objects+self.cameras}
        for camera in self.cameras:
            scene.camera = camera.ob
            bpy.context.scene.render.engine = 'BLENDER_EEVEE'
            bpy.context.scene.eevee.taa_render_samples = 1


            for ob in self.objects:
                if ob.type=='MESH' and ob.is_xraymask: # render xraymasks
                    for node in scene.node_tree.nodes:
                        if node.type == 'OUTPUT_FILE':
                            node.file_slots[0].path = f'xray_{camera.name}_'
                            if node.name == ob.name:
                                node.mute = False
                            else:
                                node.mute = True
                    for ob_here in self.objects:
                        if ob_here.type=='MESH':
                            ob_here.ob.hide_render = True
                    ob.ob.hide_render = False
                    bpy.ops.render.render()
                    for ob_here in self.objects:
                        if ob_here.type=='MESH':
                            ob_here.ob.hide_render = False
            
            bpy.context.scene.render.engine = self.global_params['engine']
            bpy.context.scene.eevee.taa_render_samples = 64
            
            for node in scene.node_tree.nodes:
                if node.type == 'OUTPUT_FILE':
                    node.file_slots[0].path = f'{camera.name}_'
                    node.mute = False
            bpy.ops.render.render()
        json.dump(annots, open(os.path.join(self.output_path, self.output_suffix, f'annots_frame{frame_index:04}.json'),'w'), indent=4)
    
    def render_sequence(self):
        scene = bpy.context.scene
        for i in range(scene.frame_start, scene.frame_end):
            scene.frame_current = i
            self.render_frame(frame_index=i)