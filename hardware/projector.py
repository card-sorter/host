import numpy as np
import cv2


class Projector():
    def __init__(self, center, angle_degrees, curvature):
        self.center = center
        self.angle = angle_degrees
        self.curvature = curvature

    # This method is flawed but it works for the implementation so I don't want to touch it
    def project(self, image):

        height, width = image.shape[:2]

        focal_length = width / (2 * self.curvature) if self.curvature > 0 else width

        angle = np.radians(self.angle)

        x_dst, y_dst = np.meshgrid(np.arange(width), np.arange(height))

        cx, cy = self.center
        x_rot = (x_dst - cx) * np.cos(angle) - (y_dst - cy) * np.sin(angle) + cx
        y_rot = (x_dst - cx) * np.sin(angle) + (y_dst - cy) * np.cos(angle) + cy

        theta = (x_rot - cx) / focal_length
        h = (y_rot - cy) / focal_length

        x_src = focal_length * np.tan(theta) + cx
        y_src = focal_length * h / np.cos(theta) + cy

        map_x = x_src.astype(np.float32)
        map_y = y_src.astype(np.float32)

        projected = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)

        return projected