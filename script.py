from os import walk
from os.path import join

import toml

_, _, filenames = next(walk('config/scripts'))

filenames = list(map(lambda p: join('config/scripts', p), filenames))

SCRIPTS = []

for file in filenames:
    data = toml.load(file)
    SCRIPTS.append(data['script'])


def findScripts(node):
    parents = node.parents
    driver = parents['__root__'].driver.key
    node_type = node.key

    result = []
    for script in SCRIPTS:
        if driver not in script['drivers']:
            continue
        if node_type != script['node_type']:
            continue
        valid = True
        for cond_node_type in script['conditions']:
            value = script['conditions'][cond_node_type]
            if not value:
                valid = False
            if value != parents[cond_node_type].data[0]:
                valid = False
        if not valid:
            continue

        result.append(['[Script] ' + script['name'], script['conn_type'], script['query']])
    return result
