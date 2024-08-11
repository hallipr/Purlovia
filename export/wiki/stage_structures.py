from typing import Any, List, Optional, cast

from automate.hierarchy_exporter import ExportFileModel, ExportModel, Field, JsonHierarchyExportStage
from ue.gathering import gather_properties
from ue.properties import FloatProperty
from ue.proxy import UEProxyStructure
from utils.log import get_logger

from .flags import gather_flags
from .types import PrimalStructure, PrimalStructureItemContainer_SupplyCrate, PrimalStructureSettings

__all__ = [
    'StructuresStage',
]

logger = get_logger(__name__)

OUTPUT_FLAGS = (
    'bDisableStructureOnElectricStorm',
    'bForceAllowInPreventionVolumes',
    'bAllowAttachToSaddle',
)


class Structure(ExportModel):
    name: str = Field(..., title="Name of the structure")
    bp: str = Field(..., title="Full blueprint path")
    flags: List[str] = Field(
        list(),
        description="Relevant boolean flags that are True for this structure",
    )
    health: Optional[FloatProperty] = Field(None)
    decayTime: Optional[float] = Field(None)
    paintableRegions: List[bool] = Field([False] * 6)


class StructuresExportModel(ExportFileModel):
    structures: List[Structure]

    class Config:
        title = "Structure data for the Wiki"


class StructuresStage(JsonHierarchyExportStage):
    def get_name(self) -> str:
        return "structures"

    def get_format_version(self) -> str:
        return "1"

    def get_use_pretty(self) -> bool:
        return bool(self.manager.config.export_wiki.PrettyJson)

    def get_ue_type(self) -> str:
        return PrimalStructure.get_ue_type()

    def get_schema_model(self):
        return StructuresExportModel

    def extract(self, proxy: UEProxyStructure) -> Any:
        structure = cast(PrimalStructure, proxy)

        # Skip the structure if it's a supply crate. There's a separate,
        # specialized export for that.
        if isinstance(proxy, PrimalStructureItemContainer_SupplyCrate):
            return None

        # Skip structures that do not have a name.
        if _is_structure_likely_base_class(structure):
            return None

        out = Structure(
            name=str(structure.DescriptiveName[0]),
            bp=proxy.get_source().fullname,
        )

        settings = None
        try:
            settings = self._get_structure_settings_proxy(structure)
        except Exception:  # pylint: disable=broad-except
            logger.warning(f'Retrieving structure settings failed for {proxy.get_source().fullname}', exc_info=True)
            return None

        out.flags = gather_flags(structure, OUTPUT_FLAGS)

        if structure.bUsesHealth[0] and structure.bCanBeDamaged[0]:
            out.health = structure.Health[0]

        if not structure.bImmuneToAutoDemolish[0]:
            out.decayTime = structure.DecayDestructionPeriod[0] * structure.DecayDestructionPeriodMultiplier[0]
            if settings:
                out.decayTime *= settings.DecayDestructionPeriodMultiplier[0]

        if structure.bAllowStructureColors[0] and structure.bUsesPaintingComponent[0]:
            for index, byte in structure.AllowStructureColorSets.items():
                out.paintableRegions[index] = byte.value == 1

        return out

    def _get_structure_settings_proxy(self, structure: PrimalStructure) -> Optional[PrimalStructureSettings]:
        result = None

        if structure.has_override('StructureSettingsClass'):
            settings_cls = structure.StructureSettingsClass[0]
            if settings_cls.value and settings_cls.value.value:
                asset = self.manager.loader.load_related(settings_cls)
                proxy: UEProxyStructure = gather_properties(asset)
                result = cast(PrimalStructureSettings, proxy)

        return result


def _is_structure_likely_base_class(structure: PrimalStructure) -> bool:
    bp = structure.get_source().fullname
    if '_Base_' in bp:
        return True

    has_name = structure.has_override('DescriptiveName')
    has_static_mesh = structure.has_override('MyStaticMesh')
    return not has_name or not has_static_mesh
