from typing import Dict, List, Tuple

from utils.log import get_logger

from .base import UEBase
from .coretypes import StripDataFlags
from .properties import Guid, NameIndex, PropertyTable

logger = get_logger(__name__)


class InstancedStaticMeshComponentObject(UEBase):

    visible_instances: List[Tuple[float, float, float]]

    def _deserialise(self, properties: PropertyTable):  # type:ignore
        lod_count = self.stream.readUInt32()

        for _ in range(lod_count):
            strip_flags = StripDataFlags(self).deserialise()

            # Light and shadow map references
            if not strip_flags.is_stripped_for_server():
                self.stream.offset += 8

            # Vertex colorization data
            if not strip_flags.is_stripped_for_custom(1):
                has_color_data = self.stream.readBool8()
                #print(has_color_data)
                if has_color_data:
                    color_strip = StripDataFlags(self).deserialise()
                    self.stream.offset += 4
                    color_num = self.stream.readUInt32()
                    #print(color_num, color_strip.is_stripped_for_server())

                    # Required for client data to be parsed.
                    if color_num > 0 and not color_strip.is_stripped_for_server():
                        self.stream.offset += 4 * color_num
                        self.stream.offset += 8

            # Painted vertices (possibly messed up struct size)
            #print(not strip_flags.is_stripped_for_editor())
            if not strip_flags.is_stripped_for_editor():
                paint_count = self.stream.readUInt32()
                #print(paint_count)
                for _ in range(paint_count):
                    self.stream.offset += 3*4 + 4*4 + 1

        # Instances are serialised as a memory dump - UE precedes this with size of the struct for safety (to prevent loading an
        # incompatible asset if the struct layout has changed).
        assert self.stream.readUInt32() == 80
        num_instances = self.stream.readUInt32()
        instances = []

        for index in range(num_instances):
            # TODO: check if instance is visible (i.e. 1 in the bitmask)

            # Each instance is described as a 4x4 matrix. Last row describes the origin.
            # Discarding scale and rotation to keep only the origin.
            self.stream.offset += 4 * 3 * 4  # 3 rows with 4 values each 4 bytes long
            x, y, z = (self.stream.readFloat(), self.stream.readFloat(), self.stream.readFloat())
            # One more value that might be used as part of scaling.
            self.stream.offset += 4
            # These are UV biases we don't need. Removed in later engine releases.
            self.stream.offset += 16

            instances.append((x, y, z))

        self._newField('visible_instances', instances)


class MaterialInstanceObject(UEBase):

    static_params: Dict[str, bool]

    def _deserialise(self, properties: PropertyTable):  # type:ignore
        num = self.stream.readUInt32()
        params = dict()
        for _ in range(num):
            name = NameIndex(self).deserialise()
            name.link()
            value = self.stream.readBool32()
            override = self.stream.readBool32()
            Guid(self).deserialise()

            if override:
                params[name.value.value] = value

        self._newField('static_params', params)


AFTER_PROPERTY_TABLE_TYPES = {
    'HierarchicalInstancedStaticMeshComponent': InstancedStaticMeshComponentObject,
    'MaterialInstanceConstant': MaterialInstanceObject,
}
