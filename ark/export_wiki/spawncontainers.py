from dataclasses import dataclass, field
from logging import NullHandler, getLogger
from typing import List, Optional

from ark.properties import gather_properties, stat_value
from ue.asset import UAsset
from ue.loader import AssetLoader, AssetNotFound

logger = getLogger(__name__)
logger.addHandler(NullHandler())


@dataclass
class SpawnGroupEntry:
    name: str
    chance: float = 0.0
    weight: float = 1.0
    npcs_to_spawn: List[str] = field(default_factory=lambda: [])
    npcs_to_spawn_chances: List[float] = field(default_factory=lambda: [])

    def as_dict(self):
        return {
            'name': self.name,
            'chance': self.chance,
            'weight': self.weight,
            'npcsToSpawn': self.npcs_to_spawn,
            'npcsToSpawnPercentageChance': self.npcs_to_spawn_chances
        }


@dataclass
class SpawnGroupLimitEntry:
    npc_class: str
    max_percent_of_desired_num: float = 1.0

    def as_dict(self):
        return {'name': self.npc_class, 'maxPercentageOfDesiredNumToAllow': self.max_percent_of_desired_num}


@dataclass
class SpawnGroupObject:
    name: str
    max_desired_enemies_num_multiplier: float = 1.0
    entries: List[SpawnGroupEntry] = field(default_factory=lambda: [])
    limits: List[SpawnGroupLimitEntry] = field(default_factory=lambda: [])

    def as_dict(self):
        return {
            "path": self.name,
            "maxDesiredNumEnemiesMultiplier": self.max_desired_enemies_num_multiplier,
            "entries": [entry.as_dict() for entry in self.entries],
            "limits": [limit.as_dict() for limit in self.limits]
        }


def _struct_entry_array_to_dict(struct_entries):
    entry_data = {}
    for struct_entry in struct_entries:
        entry_data[str(struct_entry.name)] = struct_entry.value
    return entry_data


def get_creature_name(loader, npc):
    species_asset = loader.load_related(npc)
    props = gather_properties(species_asset)
    name = stat_value(props, 'DescriptiveName', 0)
    return name


def gather_spawn_entries(loader: AssetLoader, asset: UAsset):
    properties = asset.default_export.properties.as_dict()
    entries = properties["NPCSpawnEntries"]
    if not entries:
        logger.warning(f'TODO: {asset.default_export.name} does not have any spawn entries. They are probably inherited.')
        return

    for entry in entries[0].values:
        entry_data = _struct_entry_array_to_dict(entry.values)
        entry_object = SpawnGroupEntry(str(entry_data['AnEntryName'].value))
        entry_object.weight = entry_data['EntryWeight'].value
        #str(npc.value.value.name)
        entry_object.npcs_to_spawn = [get_creature_name(loader, npc) for npc in entry_data['NPCsToSpawn'].values]
        entry_object.npcs_to_spawn_chances = [chance.value for chance in entry_data['NPCsToSpawnPercentageChance'].values]
        yield entry_object


def gather_limit_entries(loader: AssetLoader, asset: UAsset):
    properties = asset.default_export.properties.as_dict()
    entries = properties["NPCSpawnLimits"]
    if not entries:
        logger.warning(
            f'TODO: {asset.default_export.name} does not have any limit entries. They are either inherited or the species in the container are not supposed to be spawned randomly.'
        )
        return

    for entry in entries[0].values:
        entry_data = _struct_entry_array_to_dict(entry.values)
        entry_object = SpawnGroupLimitEntry(get_creature_name(
            loader, entry_data['NPCClass']))  #str(entry_data['NPCClass'].value.value.name))
        if 'MaxDesiredNumEnemiesMultiplier' in entry_data:
            entry_object.max_percent_of_desired_num = entry_data['MaxDesiredNumEnemiesMultiplier'].value
        yield entry_object


def get_spawn_entry_container_data(loader: AssetLoader, asset_name: str) -> Optional[SpawnGroupObject]:
    try:
        asset = loader[asset_name]
    except AssetNotFound:
        logger.warning(f'Spawn entry container {asset_name} does not exist. Broken reference from a map?')
        return None

    properties = asset.default_export.properties.as_dict()
    max_desired_enemy_num_mult = 1.0
    if "MaxDesiredNumEnemiesMultiplier" in properties:
        max_desired_enemy_num_mult = properties["MaxDesiredNumEnemiesMultiplier"][0].value

    entries = list(gather_spawn_entries(loader, asset))
    limits = list(gather_limit_entries(loader, asset))
    del loader.cache[asset_name]

    weight_sum = sum([entry.weight for entry in entries])
    for entry in entries:
        entry.chance = entry.weight / weight_sum
    entries.sort(key=lambda entry: entry.chance)

    return SpawnGroupObject(asset_name, max_desired_enemy_num_mult, entries, limits)
