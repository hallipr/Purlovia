'''
Creates an svg-file with regions that contain links to the according region-page
(used on the ARK: Survival Evolved Wiki)
'''

import html
import re

REGEX_INVALID_BIOME = re.compile(r'^\?+$')


def filter_biomes(biomes):
    valid_biomes = []

    for biome in biomes['biomes']:
        if not biome['boxes'] or not biome['name'].strip() or REGEX_INVALID_BIOME.search(biome['name']):
            continue

        if biome['name'] == 'Underwater':
            biome['priority'] = -1
            # Remove underwater regions in the middle of the map
            valid_boxes = []
            for box in biome['boxes']:
                if not ((box['start']['x'] > -300000 and box['end']['x'] < 300000) and
                        (box['start']['y'] > -300000 and box['end']['y'] < 300000)):
                    valid_boxes.append(box)
            biome['boxes'] = valid_boxes
        elif biome['name'] == 'Deep Ocean':
            biome['priority'] = -2

        valid_biomes.append(biome)

    return valid_biomes


def _generate_biome_rects(biome):
    for box in biome['boxes']:
        # rectangle-coords
        x1 = min(max(0, box['start']['long']), 100)
        x2 = min(max(0, box['end']['long']), 100)
        y1 = min(max(0, box['start']['lat']), 100)
        y2 = min(max(0, box['end']['lat']), 100)

        # Make sure the order is right
        if x1 > x2:
            x2, x1 = x1, x2
        if y1 > y2:
            y2, y1 = y1, y2

        w = x2 - x1
        h = y2 - y1

        # Skip if the volume's area is zero, or if out of bounds
        if w == 0 or h == 0:
            continue

        yield [round(a, 2) for a in (x1, y1, w, h)]


def generate_data(biomes):
    # Remove invalid biome entries
    valid_biomes = filter_biomes(biomes)

    # Combine regions with the same name
    index = 0
    biome_count = len(valid_biomes)
    while index < biome_count:
        j = index + 1
        while j < biome_count:
            if valid_biomes[index]['name'] == valid_biomes[j]['name']:
                valid_biomes[index]['boxes'] = valid_biomes[index]['boxes'] + valid_biomes[j]['boxes']
                del valid_biomes[j]
                biome_count -= 1
            else:
                j += 1
        index += 1

    # Sort biomes by priority
    valid_biomes.sort(key=lambda biome: biome['priority'], reverse=False)

    # Create
    out = dict()
    for biome in valid_biomes:
        out[biome['name']] = list(_generate_biome_rects(biome))
    return out
