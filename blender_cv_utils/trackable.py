import bpy
import bpy_types


class SceneObject():
    def __init__(self, ob):
        if isinstance(ob, str):
            assert ob in bpy.data.objects.keys(), 'Object with that name is not at scene'
            self._name = ob
        elif not isinstance(ob, bpy_types.Object):
            raise Exception('Not blender object')
        else:
            self._name = ob.name
    
    @property
    def name(self):
        return self._name
    
    @property
    def ob(self):
        return bpy.data.objects[self.name] # safier to call object by name each time
    
    @property
    def type(self):
        return self.ob.type
    
    def get_annotations(self, depsgraph):
        ob = depsgraph.objects[self._name]
        return {
            'type': self.type,
            'name': self.name,
            'location': tuple(ob.location),
            'scale': tuple(ob.scale),
            'rotation_euler': tuple(ob.rotation_euler),
            'matrix_local': tuple([tuple(i) for i in ob.matrix_local]),
            'matrix_basis': tuple([tuple(i) for i in ob.matrix_basis]),
            'matrix_world': tuple([tuple(i) for i in ob.matrix_world]),
            'matrix_parent_inverse': tuple([tuple(i) for i in ob.matrix_parent_inverse]),
        }
        

class MeshObject(SceneObject):
    def __init__(self, ob, is_mask=True, is_xraymask=False):
        super().__init__(ob)
        assert self.type == 'MESH'
        self.is_mask = is_mask
        self.is_xraymask = is_xraymask

    def get_annotations(self, depsgraph, **kwargs):
        super_annots = super().get_annotations(depsgraph)
        ob = depsgraph.objects[self._name]
        d = {
            'verts': [tuple(i.co) for i in ob.data.vertices], 
            'ray_cast_collision_points': {},
        }
        if 'cameras' in kwargs:
            for camera in kwargs['cameras']:
                camera_location = depsgraph.objects[camera.name].location
                ray_cast_collision_points = [tuple(bpy.context.scene.ray_cast(depsgraph, camera_location, i.co-camera_location)[1]) for i in ob.data.vertices] 
                d['ray_cast_collision_points'][camera.name] = ray_cast_collision_points

        return super_annots | d


class ArmatureObject(SceneObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert self.type == 'ARMATURE'

    def get_annotations(self, depsgraph, **kwargs):
        super_annots = super().get_annotations(depsgraph)
        ob = depsgraph.objects[self._name]

        default_data={}
        for bone in ob.data.bones:
            default_data[bone.name] = {'head_local': tuple(bone.head_local),
                                        'head': tuple(bone.head),
                                        'tail_local': tuple(bone.tail_local),
                                        'tail': tuple(bone.tail),
                                        'matrix': tuple([tuple(i) for i in bone.matrix]),
                                        'matrix_local': tuple([tuple(i) for i in bone.matrix_local]),}
        pose={}
        for bone in ob.pose.bones:
            pose[bone.name] = {'head':tuple(bone.head),
                               'tail':tuple(bone.tail),
                               'matrix':tuple([tuple(i) for i in bone.matrix]),
                               'ray_cast_collision_objects_bonehead':{},
                               'ray_cast_collision_objects_bonetail':{},
                              }
            if 'cameras' in kwargs:
                for camera in kwargs['cameras']:
                    camera_location = depsgraph.objects[camera.name].location
                    raycast_data = bpy.context.scene.ray_cast(depsgraph, camera_location, bone.head-camera_location)
                    pose[bone.name]['ray_cast_collision_objects_bonehead'][camera.name] = raycast_data[4].name if raycast_data[4] is not None else None
                    raycast_data = bpy.context.scene.ray_cast(depsgraph, camera_location, bone.tail-camera_location)
                    pose[bone.name]['ray_cast_collision_objects_bonetail'][camera.name] = raycast_data[4].name if raycast_data[4] is not None else None

        d = {
            'default_data': default_data,
            'pose': pose,
            'childrens': [i.name for i in self.ob.children],
        }
        return super_annots | d
    


class CameraObject(SceneObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert self.type == 'CAMERA'

    def get_annotations(self, depsgraph, **kwargs):
        super_annots = super().get_annotations(depsgraph)
        ob = depsgraph.objects[self._name]
        d = {
            'lens': ob.data.lens,
            'lens_unit': ob.data.lens_unit,
            'angle_x': ob.data.angle_x,
            'angle_y': ob.data.angle_y,
            'sensor_fit': ob.data.sensor_fit,
            'sensor_height': ob.data.sensor_height,
            'sensor_width': ob.data.sensor_width,
        }
        return super_annots | d