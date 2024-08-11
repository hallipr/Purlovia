from typing import Dict

from export.wiki.types import PrimalInventoryComponent
from ue.hierarchy import inherits_from


def convert_value_mults(inventory: PrimalInventoryComponent, name: str) -> Dict[str, float]:
    out = dict()
    values = inventory.get(name, fallback=None)

    if values and values.values:
        for modifier in values:
            info = modifier.as_dict()
            item_ref = info['ItemClass']
            mult = info['ItemMultiplier']

            if not item_ref or not item_ref.value or not item_ref.value.value:
                continue

            item = item_ref.value.value.fullname
            if item not in out and not any(inherits_from(item, other, safe=True) for other in out.keys()):
                out[item] = mult

    return out
