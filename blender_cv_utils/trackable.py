import sys
sys.path.append('C:/Users/ivand/Documents/Projects/Pigs/Blender-CV-Utils')

import bpy_types
import bpy


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
    
    @property
    def modifiers(self):
        return list(self.ob.modifiers)
    
    @property
    def constraints(self):
        return list(self.ob.constraints)

    def make_active(self):
        bpy.ops.object.select_all(action='DESELECT')
        self.ob.select_set(True)
        bpy.context.view_layer.objects.active = self.ob

    def _apply_modifiers_and_constraints(self):
        if len(list(self.modifiers))==0: # and len(list(self.constraints))==0  
            return False, self.ob
        
        self.make_active()
        bpy.ops.object.duplicate()
        for i in bpy.context.active_object.modifiers:
            bpy.ops.object.modifier_apply(modifier=i.name)
        # for i in bpy.context.active_object.constraints:
        #     bpy.ops.constraint.apply(constraint=i.name, owner='OBJECT')
        return True, bpy.context.active_object

    def get_annotations(self):
        return {
            'type': self.type,
            'name': self.name,
            'location': tuple(self.ob.location),
            'scale': tuple(self.ob.scale),
            'rotation_euler': tuple(self.ob.rotation_euler),
        }


class MeshObject(SceneObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert self.type == 'MESH'

    def get_annotations(self):
        super_annots = super().get_annotations()
        ret, temp_ob = self._apply_modifiers_and_constraints()
        d = {
            'verts': [tuple(i.co) for i in temp_ob.data.vertices]
        }
        if ret:
            bpy.ops.object.delete()
        return super_annots | d
    


class CameraObject(SceneObject):
    def __init__(self, ob):
        super().__init__(ob)
        assert self.type == 'CAMERA'

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


# c = MeshObject('Cube')
# c.get_annotations()

