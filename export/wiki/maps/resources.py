from typing import Dict, List, Optional, Tuple

from ark.overrides import OverrideSettings
from ue.asset import ExportTableItem
from ue.utils import get_assetpath_from_assetname, get_leaf_from_assetname
from utils.log import get_logger

logger = get_logger(__name__)

LEVEL_NAME_EXTRA_SUFFIX = {
    # Genesis 2 asteroid fields
    # Level names found in /Game/Genesis2/CoreBlueprints/Environment/DayCycleManager_Gen2
    # Ambergris
    'Space_Backdrop_Asteroids_0': 'rot0',
    'Space_Asteroids_0_Geo': 'rot0',
    # Crystal
    'Space_Backdrop_Asteroids_1': 'rot1',
    'Space_Asteroids_1_Geo': ' rot1',
    # Sulfur
    'Space_Backdrop_Asteroids_2': 'rot2',
    'Space_Asteroids_2_Geo': 'rot2',
    # Element Shard
    'Space_Backdrop_Asteroids_3': 'rot3',
    'Space_Asteroids_3_Geo': 'rot3',
    # Obsidian
    'Space_Backdrop_Asteroids_4': 'rot4',
    'Space_Asteroids_4_Geo': 'rot4',
    # Oil
    'Space_Backdrop_Asteroids_5': 'rot5',
    'Space_Asteroids_5_Geo': 'rot5',
    # Element Dust
    'Space_Backdrop_Asteroids_6': 'rot6',
    'Space_Asteroids_6_Geo': 'rot6',
    # Black Pearls
    'Space_Backdrop_Asteroids_7': 'rot7',
    'Space_Asteroids_7_Geo': 'rot7',
}

ResourceNodesByType = Dict[str, List[Tuple[float, float, float, bool, Optional[str]]]]

# TODO: Move to overrides.yaml
CAVE_LEVEL_IDENTIFIERS = (
    'Cave',
    'Dungeon',
)

a = set()


def collect_harvestable_resources(export: ExportTableItem, overrides: OverrideSettings, out: ResourceNodesByType):
    assert export.properties
    assert export.extended_data

    # Retrieve the harvesting component class and check if it's valid.
    component = export.properties.get_property('AttachedComponentClass', fallback=None)
    if not component or not component.value or not component.value.value:
        return

    # Get a resource type identifier if one is available. Skip otherwise.
    component_bp = component.value.value.namespace.value.fullname
    if overrides.exclude_harvestables.get(component_bp, False):
        return
    if component_bp not in a:
        print(component_bp)
        a.add(component_bp)
    component_name = str(component.value.value.name)

    if component_name == 'RockHarvestComponent_C':
        static_mesh = export.properties.get_property('StaticMesh', fallback=None)
        if not static_mesh or not static_mesh.value or not static_mesh.value.value:
            return
        if not 'Ground_Rocks' in str(static_mesh.value.value.namespace.value.fullname):
            return

    # Query a tag for the resource type depending on level (Genesis 2 rotations, Fjordur subrealms)
    level_name = get_leaf_from_assetname(export.asset.assetname)
    modifier = LEVEL_NAME_EXTRA_SUFFIX.get(level_name, None)

    # Naively determine if the level might be related to a cave.
    is_likely_cave = any(ident in export.asset.assetname for ident in CAVE_LEVEL_IDENTIFIERS)

    # Copy visible instances from export's extended data into the world.
    for x, y, z in export.extended_data.visible_instances:
        out[component_name].append((x, y, z, is_likely_cave, modifier))
