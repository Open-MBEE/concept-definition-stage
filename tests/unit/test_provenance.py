"""REQ-K4.1 — every committed triple carries PROV-O attribution. (P3, red)"""
from cds.mcp import provenance


def test_stamp_attaches_provenance():
    provenance.stamp([], user="u", session="s", model="m")  # NotImplementedError -> red
