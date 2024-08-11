import re
from collections.abc import MutableMapping as Map
from copy import deepcopy
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Union

import yaml
from pydantic import BaseModel, Field

from config import OVERRIDE_FILENAME
from ue.utils import get_assetpath_from_assetname

__all__ = [
    'ColorRegionSettings',
    'OverrideSettings',
    'OverridesFile',
    'get_overrides_for_species',
    'get_overrides_for_map',
    'get_overrides_for_mod',
    'get_overrides_global',
    'get_overrides',
    'any_regexes_match',
]


class ColorRegionSettings(BaseModel):
    '''Color region settings for species'''
    capitalize: Optional[bool] = Field(
        None,
        description="Whether to capitalize the first character of region names",
    )
    default_name: Optional[str] = Field(
        None,
        description="What to name regions that have no name",
    )
    nullify_name_regexes: Dict[str, str] = Field(
        dict(),
        description="Region are nullified if their names wholely match any of these regexes (key names are ignored)",
    )
    useless_name_regexes: Dict[str, str] = Field(
        dict(),
        description="Region names that will be replaced by the default_name",
    )
    region_names: Dict[int, Optional[str]] = Field(
        dict(),
        description="Override individual region names, in for dict form `region_num: \"name\"`",
    )


class TamingMethod(str, Enum):
    none = 'none'
    awake = 'awake'
    knockout = 'knockout'


class MapBoundariesSettings(BaseModel):
    '''Boundary settings for maps'''
    border_top: float = 0
    border_left: float = 0
    border_right: float = 100
    border_bottom: float = 100


class OverrideSettings(BaseModel):
    '''Common override settings that can be applied to defaults, mods, maps, and individual species'''
    # General settings
    skip_export: Optional[bool] = Field(
        False,
        description='Set to true to leave this data out of the exported data files',
    )
    include_in_stages: Dict[str, bool] = dict()
    descriptive_name: Optional[str] = Field(
        None,
        description="Override the name of this entity",
    )

    # Variants, currently only applying to species
    add_variants: Dict[str, bool] = Field(
        dict(),
        description="Explicitly add variants to this entity, in the dict form `varient: true`",
    )
    remove_variants: Dict[str, bool] = Field(
        dict(),
        description="Explicitly remove variants from this entity, in for dict form `variant: true`",
    )
    variants_from_flags: Dict[str, Union[str, List[str]]] = Field(
        dict(),
        description="Variants that will be added if the given UE flag field is present and true",
    )
    variant_renames: Dict[str, Union[str, List[str]]] = Field(
        dict(),
        description="Rename these variants, if present, in the dict form `fromname: toname`",
    )
    name_variants: Dict[str, Union[str, List[str]]] = Field(
        dict(),
        description="Variants that will be added if the supplied regex matches the descriptive name",
    )
    classname_variant_parts: Dict[str, bool] = Field(
        dict(),
        description="Parts of a classname that will be added as a variant, matching _Variant or Variant_",
    )
    pathname_variant_parts: Dict[str, bool] = Field(
        dict(),
        description="Parts of an asset path that will be added as a variant, matching _Variant or Variant_",
    )
    pathname_variant_components: Dict[str, bool] = Field(
        dict(),
        description="Parts of an asset path that will be added as a variant, matching /Variant/ only",
    )
    variants_to_skip_export: Dict[str, bool] = Field(
        dict(),
        description="If these variants are found, the object will not be exported in all cases",
    )
    variants_to_skip_export_asb: Dict[str, bool] = Field(
        dict(),
        description="If these variants are found, the object will not be exported for ASB",
    )
    variants_to_remove_name_parts: Dict[str, str] = Field(
        dict(),
        description="If these variants are found, remove the given part of the descriptive name",
    )

    # Species
    color_regions: ColorRegionSettings = ColorRegionSettings()
    species_remaps: Dict[str, str] = Field(
        dict(),
        description="Mapping from old to new species blueprint paths",
    )
    taming_method: Optional[TamingMethod] = Field(
        None,
        description="Overrides the taming method of the species.",
    )

    # Maps
    svgs: MapBoundariesSettings = Field(
        MapBoundariesSettings(),
        title="SVGs",
        description="SVG map generation boundaries",
    )
    exclude_harvestables: Dict[str, bool] = Field(
        dict(),
        description="Harvest components that will not have any nodes emitted for them",
    )


class SanityCheckSettings(BaseModel):
    min_species: Dict[str, int] = dict()
    min_items: Dict[str, int] = dict()
    min_maps: Dict[str, int] = dict()
    ignore_maps: List[str] = list()


class RewriteSettings(BaseModel):
    assets: Dict[str, str] = dict()


class OverridesFile(BaseModel):
    '''Purlovia data overrides file'''
    defaults: OverrideSettings = OverrideSettings()
    mods: Dict[str, OverrideSettings] = dict()
    items: Dict[str, OverrideSettings] = dict()
    species: Dict[str, OverrideSettings] = dict()
    maps: Dict[str, OverrideSettings] = dict()

    sanity_checks: SanityCheckSettings = SanityCheckSettings()
    rewrites: RewriteSettings = RewriteSettings()

    class Config:
        title = 'Purlovia Overrides'


DEFAULT_COLORREGIONSETTINGS = ColorRegionSettings(
    capitalize=True,
    default_name='Unknown',
).dict(exclude_unset=True)

DEFAULT_OVERRIDES = OverridesFile(
    defaults=OverrideSettings(**DEFAULT_COLORREGIONSETTINGS),
    mods=dict(),
    species=dict(),
    maps=dict(),
).dict(exclude_unset=True)


@lru_cache()
def get_overrides() -> OverridesFile:
    with open(OVERRIDE_FILENAME, 'rt', encoding='utf-8') as f:
        raw_data = yaml.safe_load(f)

    data = OverridesFile(**raw_data)
    return data


@lru_cache(maxsize=1)
def _get_overrides_global_dict() -> Dict:
    config_file = get_overrides()
    settings: Dict[str, Any] = dict()
    nested_update(settings, DEFAULT_OVERRIDES)
    nested_update(settings, config_file.defaults.dict(exclude_unset=True))
    return settings


@lru_cache(maxsize=1)
def get_overrides_global() -> OverrideSettings:
    settings = _get_overrides_global_dict()
    return OverrideSettings(**settings)


@lru_cache(maxsize=10)
def _get_overrides_for_mod_dict(modid: str) -> Dict:
    modid = modid or ''
    config_file = get_overrides()
    settings: Dict[str, Any] = dict()
    nested_update(settings, _get_overrides_global_dict())
    nested_update(settings, config_file.mods.get(modid, OverrideSettings()).dict(exclude_unset=True))
    return settings


@lru_cache(maxsize=10)
def get_overrides_for_mod(modid: str) -> OverrideSettings:
    modid = modid or ''
    settings: Dict[str, Any] = dict()
    nested_update(settings, _get_overrides_for_mod_dict(modid))
    return OverrideSettings(**settings)


@lru_cache(maxsize=100)
def _get_overrides_for_item_dict(item: str, modid: str) -> Dict:
    modid = modid or ''
    config_file = get_overrides()
    settings: Dict[str, Any] = dict()
    nested_update(settings, _get_overrides_for_mod_dict(modid))
    nested_update(settings, config_file.items.get(item, OverrideSettings()).dict(exclude_unset=True))
    return settings


@lru_cache(maxsize=1024)
def get_overrides_for_item(item: str, modid: str) -> OverrideSettings:
    settings = _get_overrides_for_item_dict(item, modid)
    return OverrideSettings(**settings)


@lru_cache(maxsize=100)
def _get_overrides_for_species_dict(species: str, modid: str) -> Dict:
    modid = modid or ''
    config_file = get_overrides()
    settings: Dict[str, Any] = dict()
    nested_update(settings, _get_overrides_for_mod_dict(modid))
    nested_update(settings, config_file.species.get(species, OverrideSettings()).dict(exclude_unset=True))
    return settings


@lru_cache(maxsize=1024)
def get_overrides_for_species(species: str, modid: str) -> OverrideSettings:
    settings = _get_overrides_for_species_dict(species, modid)
    return OverrideSettings(**settings)


@lru_cache(maxsize=16)
def _get_overrides_for_map_dict(level_asset: str, modid: str) -> Dict:
    modid = modid or ''
    folder = get_assetpath_from_assetname(level_asset)
    config_file = get_overrides()
    settings: Dict[str, Any] = dict()
    nested_update(settings, _get_overrides_for_mod_dict(modid))
    nested_update(settings, config_file.maps.get(folder, OverrideSettings()).dict(exclude_unset=True))
    nested_update(settings, config_file.maps.get(level_asset, OverrideSettings()).dict(exclude_unset=True))
    return settings


@lru_cache(maxsize=128)
def get_overrides_for_map(level: str, modid: str) -> OverrideSettings:
    settings = _get_overrides_for_map_dict(level, modid)
    return OverrideSettings(**settings)


def any_regexes_match(source: Union[Dict[str, str], List[str]], target: str, flags: int = re.IGNORECASE):
    regexes: Iterable[str] = source.values() if isinstance(source, Map) else source
    for search in regexes:
        if search and re.match(search, target, flags):
            return True

    return False


def nested_update(d, v):
    for key in v:
        if key in d and isinstance(d[key], Map) and isinstance(v[key], Map):
            nested_update(d[key], v[key])
        else:
            d[key] = deepcopy(v[key])
    return d


if __name__ == "__main__":
    with open('schema/overrides.yaml.json', 'wt', encoding='utf-8') as f:
        schema = OverridesFile.schema_json(indent='\t')
        f.write(schema)
