# flake8: noqa

#%% Setup

from interactive_utils import *  # pylint: disable=wrong-import-order

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

#%% Config
map = sys.argv[1]
species_files = ['', 'CrystalIsles-CrystalIsles']

#%% Species info
tamability = dict()
names = dict()
for fname in species_files:
    with open('output/data/wiki/' + fname + '/species.json', 'rt') as fp:
        data = json.load(fp)

    for species in data['species']:
        names[species['bp']] = species['name'].strip()
        tamability[species['bp']] = 'isTameable' in species.get('flags', [])

#%% Spawn groups initialization
CLEAN_UP = r'(Dino|)SpawnEntries_?'
spawns = dict()
with open('output/processed/wiki-maps/' + map + '/stage1.json', 'rt') as fp:
    data = json.load(fp)

for zone in data['zones']:
    container = zone['container']
    if container not in spawns:
        name = container.rsplit('.')[1][:-2]
        name = re.sub(CLEAN_UP, '', name, re.IGNORECASE)
        name = name.strip('_')

        spawns[container] = dict(
            n=name,
            e=list(),
            s=list(),
        )

#%% Species
wild_species = set()
for bp, converted_info in spawns.items():
    out = converted_info['e']
    container = data['containers'][bp]

    weight_sum = sum(x['weight'] for x in container['entries'])

    for group in container['entries']:
        creatures = list()

        for species in group['species']:
            if species['bp'] in names:
                wild_species.add(species['bp'])
                creatures.append(dict(
                    n=names[species['bp']],
                    c=round(species['chance'], 3),
                ))

        if creatures:
            out.append(dict(
                n=group['name'],
                c=round(group['weight'] / weight_sum, 3),
                s=creatures,
            ))

#%% Spawn locations
for zone in data['zones']:
    locs = zone['locations']
    points = zone['points']

    out = dict(
        f=zone['npcCount'],
        u=1 if zone['untameable'] else 0,
        l=list(),
    )

    if locs:
        for loc in locs:
            out['l'].append((
                round(loc['start']['long'], 2),  # x1
                round(loc['start']['lat'], 2),  # y1
                round(loc['end']['long'], 2),  # x2
                round(loc['end']['lat'], 2),  # y2
            ))

    if points:
        for point in points:
            out['l'].append((
                round(point['long'], 2),  # x
                round(point['lat'], 2),  # y
            ))

    spawns[zone['container']]['s'].append(out)

#%% Merge similar
for _, data in spawns.items():
    coded_lookup = defaultdict(list)
    for spawner in data['s']:
        key = (spawner['f'], spawner['u'])
        coded_lookup[key] += spawner['l']

    new_spawners = []
    for key, locs in coded_lookup.items():
        packed = dict()
        packed['f'] = key[0]
        if key[1]:
            packed['u'] = key[1]
        packed['l'] = locs
        new_spawners.append(packed)
    data['s'] = new_spawners

#%% Save
with open('output/spawnmap.json', 'wt') as fp:
    json.dump(list(spawns.values()), fp, separators=(',', ':'))

untamability = filter(lambda x: not x[1] and x[0] in wild_species, tamability.items())
untamability = {names[b]: 0 if t else 1 for b, t in untamability}
tamability_file = Path('output/tamability.json')
untamability_final = tamability_file.exists() and json.load(tamability_file.open('rt')) or {}
untamability_final.update(untamability)
untamability_final = dict(sorted(untamability_final.items()))
with tamability_file.open('wt') as fp:
    json.dump(untamability_final, fp, separators=(',', ':'))
