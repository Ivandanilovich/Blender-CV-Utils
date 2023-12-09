import torch
from scipy.spatial.transform import Rotation
import numpy as np
import einops


def _get_sensor_size(sensor_fit, sensor_x, sensor_y):
    if sensor_fit == 'VERTICAL':
        return sensor_y
    return sensor_x


def _get_sensor_fit(sensor_fit, size_x, size_y):
    if sensor_fit == 'AUTO':
        if size_x >= size_y:
            return 'HORIZONTAL'
        else:
            return 'VERTICAL'
    return sensor_fit


# Build intrinsic camera parameters from Blender camera data
#
# See notes on this in
# blender.stackexchange.com/questions/15102/what-is-blenders-camera-projection-matrix-model
# as well as
# https://blender.stackexchange.com/a/120063/3581
def get_calibration_matrix_K(resolution_x, resolution_y, sensor_width, sensor_height, lens, sensor_fit,
                             shift_x=0, shift_y=0,
                             pixel_aspect_x=1, pixel_aspect_y=1, resolution_percentage=100):
    resolution_x_in_px = resolution_x * resolution_percentage/100
    resolution_y_in_px = resolution_y * resolution_percentage/100
    sensor_size_in_mm = _get_sensor_size(
        sensor_fit, sensor_width, sensor_height)
    sensor_fit = _get_sensor_fit(
        sensor_fit, pixel_aspect_x * resolution_x_in_px, pixel_aspect_y * resolution_y_in_px)
    pixel_aspect_ratio = pixel_aspect_y / pixel_aspect_x
    if sensor_fit == 'HORIZONTAL':
        view_fac_in_px = resolution_x_in_px
    else:
        view_fac_in_px = pixel_aspect_ratio * resolution_y_in_px
    pixel_size_mm_per_px = sensor_size_in_mm / lens / view_fac_in_px
    s_u = 1 / pixel_size_mm_per_px
    s_v = 1 / pixel_size_mm_per_px / pixel_aspect_ratio

    # Parameters of intrinsic calibration matrix K
    u_0 = resolution_x_in_px / 2 - shift_x * view_fac_in_px
    v_0 = resolution_y_in_px / 2 + shift_y * view_fac_in_px / pixel_aspect_ratio
    skew = 0  # only use rectangular pixels

    K = np.array([(s_u, skew, u_0),
                  (0,  s_v, v_0),
                  (0,    0,   1)])
    return K


def get_RT_matrix(matrix_world):
    # bcam stands for blender camera
    R_bcam2cv = np.array(((1, 0,  0),
                          (0, -1, 0),
                          (0, 0, -1)))

    matrix_world = np.array(matrix_world)
    R_world2bcam = matrix_world[:3, :3].T
    T_world2bcam = -1*R_world2bcam @ matrix_world[:3:, 3]

    R_world2cv = R_bcam2cv@R_world2bcam
    T_world2cv = R_bcam2cv@T_world2bcam

    RT = np.concatenate((R_world2cv, T_world2cv[:, None]), axis=1)
    return RT


def apply_object_matrix_world(verts, matrix_world):
    matrix_world = np.array(matrix_world)
    verts = np.array(verts)

    if matrix_world.shape[0] == 4:
        matrix_world = matrix_world[:3]

    ones = np.ones((verts.shape[-2], 1))
    verts = np.concatenate((verts, ones), axis=1)
    matrix_world = einops.repeat(matrix_world, 'r c -> points r c', points=verts.shape[0])
    return torch.einsum('bcr,br->bc', torch.tensor(matrix_world), torch.tensor(verts)).numpy()


def project_points(points, **kwargs):
    K = get_calibration_matrix_K(resolution_x=kwargs['resolution_x'],
                                 resolution_y=kwargs['resolution_y'],
                                 sensor_width=kwargs['sensor_width'],
                                 sensor_height=kwargs['sensor_height'],
                                 lens=kwargs['lens'],
                                 sensor_fit=kwargs['sensor_fit'],
                                 pixel_aspect_x=kwargs['pixel_aspect_x'],
                                 pixel_aspect_y=kwargs['pixel_aspect_y'],
                                 resolution_percentage=kwargs['resolution_percentage'],)
    RT = get_RT_matrix(matrix_world=kwargs['matrix_world'])

    P = K @ RT
    ones = np.ones((points.shape[-2], 1))
    points = np.concatenate((points, ones), axis=1)
    P = einops.repeat(P, 'r c -> points r c', points=points.shape[0])
    projected = torch.einsum('bcr,br->bc', torch.tensor(P), torch.tensor(points))
    projected = (projected / projected[:, -1][:, None])[:, :2]
    return projected
