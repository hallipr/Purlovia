from typing import Optional, Tuple, Union

from automate.hierarchy_exporter import ExportModel, Field
from ue.properties import BoolProperty, FloatProperty

from ..models import MinMaxRange


class ItemStatEffect(ExportModel):
    value: FloatProperty = Field(
        ...,
        description="Amount to change stat by",
    )
    descriptionIndex: int = Field(
        ...,
        description="Index of stat description text (from PGD)",
    )

    pctOf: Optional[str] = Field(
        None,
        description="",
    )
    pctAbsRange: Optional[MinMaxRange] = None

    setValue: BoolProperty = Field(default_factory=lambda: BoolProperty.create(False))
    setAddValue: BoolProperty = Field(default_factory=lambda: BoolProperty.create(False))
    forceUseOnDino: BoolProperty = Field(default_factory=lambda: BoolProperty.create(False))
    allowWhenFull: BoolProperty = Field(default_factory=lambda: BoolProperty.create(True))

    qualityMult: FloatProperty = Field(default_factory=lambda: FloatProperty.create(1.0))
    duration: Optional[Union[float, FloatProperty]] = None

    # 'bContinueOnUnchangedValue = (BoolProperty) False',
    # 'bResetExistingModifierDescriptionIndex = (BoolProperty) False',
    # 'LimitExistingModifierDescriptionToMaxAmount = (FloatProperty) 0.0',
    # 'ItemQualityAddValueMultiplier = (FloatProperty) 1.0',
    # 'StopAtValueNearMax = (ByteProperty) ByteProperty(EPrimalCharacterStatusValue, EPrimalCharacterStatusValue::MAX)',
    # 'ScaleValueByCharacterDamageType = (ObjectProperty) None'),


def convert_status_effect(entry) -> Tuple[str, ItemStatEffect]:
    d = entry.as_dict()
    stat_name = d['StatusValueType'].get_enum_value_name().lower()

    result = ItemStatEffect(
        value=d['BaseAmountToAdd'],
        descriptionIndex=d['StatusValueModifierDescriptionIndex'],
    )

    pctOfMax = d['bPercentOfMaxStatusValue']
    pctOfCur = d['bPercentOfCurrentStatusValue']
    if pctOfCur or pctOfMax:
        result.pctOf = 'max' if pctOfMax else 'current'

    pctMin = d['PercentAbsoluteMinValue']
    pctMax = d['PercentAbsoluteMaxValue']
    if pctMin != 0 or pctMax != 0:
        result.pctAbsRange = MinMaxRange(min=d['PercentAbsoluteMinValue'], max=d['PercentAbsoluteMaxValue'])

    result.setValue = d['bSetValue']
    result.setAddValue = d['bSetAdditionalValue']
    result.forceUseOnDino = d['bForceUseStatOnDinos']
    result.allowWhenFull = d['bDontRequireLessThanMaxToUse']

    if d['bUseItemQuality']:
        result.qualityMult = d['ItemQualityAddValueMultiplier']

    if d['bAddOverTimeSpeedInSeconds']:
        result.duration = d['AddOverTimeSpeed']
    else:
        if d['AddOverTimeSpeed'] == 0:
            # Assume instant
            result.duration = 0.0
        else:
            # Duration = amount / speed, rounded to 1dp
            result.duration = round(abs(d['BaseAmountToAdd']) / d['AddOverTimeSpeed'], 2)

    return (stat_name, result)
