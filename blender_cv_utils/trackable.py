import sys
sys.path.append('C:/Users/ivand/Documents/Projects/Pigs/Blender-CV-Utils')


import bpy_types
import numpy as np
import bpy


class TObject():
    def __init__(self, ob: bpy_types.Object):
        self.ob = ob
        assert len(ob.modifiers) == 0
        assert len(ob.constraints) == 0

    def get_annotations(self):
        d = {
            'type': self.ob.type,
            'name': self.ob.name,
            'location': np.array(self.ob.location),
            'scale': np.array(self.ob.scale),
            'rotation_euler': np.array(self.ob.rotation_euler),
        }
        return d


class MeshObject(TObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert ob.type == 'MESH'

    def get_annotations(self):
        super_annots = super().get_annotations()
        d = {
            'verts': np.array([i.co for i in self.ob.data.vertices])
        }
        return super_annots | d


class CameraObject(TObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert ob.type == 'CAMERA'

    def get_annotations(self):
        super_annots = super().get_annotations()
        d = {
            'lens': self.ob.data.lens,
            'lens_unit': self.ob.data.lens_unit,
            'angle_x': self.ob.data.angle_x,
            'angle_y': self.ob.data.angle_y,
            'sensor_fit': self.ob.data.sensor_fit,
            'sensor_height': self.ob.data.sensor_height,
            'sensor_width': self.ob.data.sensor_width,
        }
        return super_annots | d


SUPPORTED_OBJECT_TYPES = {
    'CAMERA': CameraObject,
    'MESH': MeshObject,
    # 'ARMATURE': None
}


class BlenderObject():
    def __init__(self, ob):
        if isinstance(ob, str):
            assert ob in bpy.data.objects.keys(), 'Object with that name is not at scene'
            ob = bpy.data.objects[ob]
        elif not isinstance(ob, bpy_types.Object):
            raise Exception('Not blender object')
        self.ob = ob
        self.type = self.ob.type
        self.name = self.ob.name

    def make_active(self):
        bpy.ops.object.select_all(action='DESELECT')
        self.ob.select_set(True)
        bpy.context.view_layer.objects.active = self.ob


# facade pattern: ob can be different types
class TrackObject(BlenderObject):
    def __init__(self, ob):
        super().__init__(ob)
        self.ob_wrap = SUPPORTED_OBJECT_TYPES[self.type](self.ob)
        
    def get_annotations(self):
        return self.ob_wrap.get_annotations()


# tob = TrackObject('Camera')
# print(tob.ob)
# print(tob.get_annotations())
