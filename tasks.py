"""Tasks for maintaining the project.

Execute 'invoke --list' for guidance on using Invoke
"""

from invoke.collection import Collection
from invokelint import _clean
from invokelint import dist
from invokelint import lint
from invokelint import style
from invokelint import test

ns = Collection()
ns.add_collection(Collection.from_module(_clean), name="clean")
ns.add_collection(Collection.from_module(dist))
ns.add_collection(Collection.from_module(lint))
ns.add_collection(Collection.from_module(style))
ns.add_collection(Collection.from_module(test))
