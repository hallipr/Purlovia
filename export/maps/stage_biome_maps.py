import re
from pathlib import Path
from typing import Optional

from ark.mod import get_official_mods
from ark.overrides import get_overrides_for_map
from automate.jsonutils import save_as_json
from utils.log import get_logger

from .region_maps.svg import generate_data
from .stage_base import ProcessingStage

logger = get_logger(__name__)

__all__ = [
    'ProcessBiomeMapsStage',
]

REGEX_INVALID_BIOME = r'^\?+$'


class ProcessBiomeMapsStage(ProcessingStage):

    def get_name(self) -> str:
        return "biome_maps"

    def extract_core(self, _: Path):
        # Find data of maps with biomes
        map_set = self.find_official_maps(True, keyword='biomes')

        for _, data_path in map_set:
            self.process(self.wiki_path / data_path, None)

    def extract_mod(self, _: Path, modid: str):
        mod_data = self.manager.arkman.getModData(modid)
        assert mod_data
        if int(mod_data.get('type', 1)) != 2 and modid not in get_official_mods():
            # Mod is not a map, skip it.
            return

        # Find data of maps with biomes
        map_set = self.find_maps(modid, keyword='biomes')

        for _, data_path in map_set:
            self.process(self.wiki_path / data_path, modid)

    def get_output_path(self, map_name: str, modid: Optional[str]) -> Path:
        if not modid:
            # Core maps
            #   processed/wiki-maps/regions/Map.json
            return (self.output_path / 'regions' / map_name).with_suffix('.json')

        # Mods
        #   processed/wiki-maps/regions/Id-Mod.json
        return (self.output_path / 'regions' / self.get_mod_subroot_name(modid)).with_suffix('.svg')

    def process(self, in_path: Path, modid: Optional[str]):
        map_name = in_path.name
        logger.info(f'Processing data of map: {map_name}')

        # Load exported data
        data_biomes = self.load_json_file(in_path / 'biomes.json')
        if not data_biomes:
            logger.debug('Data required by the processor is missing or invalid. Skipping.')
            return

        data = generate_data(data_biomes)

        # Emit file.
        save_as_json(data, self.get_output_path(map_name, modid), False)
