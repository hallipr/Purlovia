from typing import Any, Dict, List, Optional, Set, Tuple, cast

from ark.gathering import gather_dcsc_properties
from ark.overrides import OverrideSettings, get_overrides_for_species
from automate.hierarchy_exporter import ExportFileModel, ExportModel, Field, JsonHierarchyExportStage
from export.wiki.types import PrimalInventoryComponent
from ue.asset import UAsset
from ue.loader import AssetLoadException
from ue.properties import FloatProperty, IntProperty, StringLikeProperty, StringProperty
from ue.proxy import UEProxyStructure
from utils.log import get_logger

from .flags import gather_flags
from .inventories.modifiers import convert_value_mults
from .models import IntLike

__all__ = [
    'InventoriesStage',
]

logger = get_logger(__name__)

OUTPUT_FLAGS = ('bIgnoreMaxInventoryItems', )


class Inventory(ExportModel):
    bp: str = Field(
        ...,
        title="Full blueprint path",
    )
    name: str = ''
    flags: List[str] = Field([])

    slots: Optional[IntProperty] = None

    weightModifiers: Dict[str, float] = Field(dict())
    spoilTimeModifiers: Dict[str, float] = Field(dict())


class InventoriesExportModel(ExportFileModel):
    inventories: List[Inventory]

    class Config:
        title = "Inventory data for the Wiki"


class InventoriesStage(JsonHierarchyExportStage):
    def get_name(self) -> str:
        return 'inventories'

    def get_use_pretty(self) -> bool:
        return bool(self.manager.config.export_wiki.PrettyJson)

    def get_format_version(self):
        return "1"

    def get_ue_type(self):
        return PrimalInventoryComponent.get_ue_type()

    def get_schema_model(self):
        return InventoriesExportModel

    def extract(self, proxy: UEProxyStructure) -> Any:
        inventory: PrimalInventoryComponent = cast(PrimalInventoryComponent, proxy)

        # Skip inventories that generate loot - data here will be redundant.
        if _does_generate_loot(inventory):
            return None

        out = Inventory(
            bp=inventory.get_source().fullname,
            name=str(inventory.InventoryNameOverride[0]),
            flags=gather_flags(inventory, OUTPUT_FLAGS),
        )

        if 'bIgnoreMaxInventoryItems' in out.flags:
            out.slots = inventory.MaxInventoryItems[0]

        out.weightModifiers = convert_value_mults(inventory, 'ItemClassWeightMultipliers')
        out.spoilTimeModifiers = convert_value_mults(inventory, 'ItemSpoilingTimeMultipliers')

        return out


def _does_generate_loot(inventory: PrimalInventoryComponent) -> bool:
    def _is_valid(name: str) -> bool:
        ref = inventory.get(name, fallback=None)
        return ref and ref.value and ref.value.value

    def _is_array_not_empty(name: str) -> bool:
        ref = inventory.get(name, fallback=None)
        return ref and ref.values

    if _is_valid('ItemSetsOverride') or _is_array_not_empty('ItemSets') or _is_valid(
            'AdditionalItemSetsOverride') or _is_array_not_empty('AdditionalItemSets'):
        return True

    return False
