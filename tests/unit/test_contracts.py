"""The cross-component seams: oracle + store contracts, satisfied by their reference impls."""
from rdflib import Graph

from cds import contracts
from cds.core.flexo import FlexoBackend, InMemoryFlexoBackend


def test_oracle_contract_satisfied_in_process() -> None:
    oracle: contracts.ConformanceOracle = contracts.InProcessOracle()
    result = oracle.check(Graph(), check_conflicts=True)
    assert result.conforms is True  # empty instance graph trivially conforms
    assert result.findings == ()


def test_model_store_contract_is_flexo_backend() -> None:
    assert contracts.ModelStore is FlexoBackend  # one contract, not a divergent copy
    store: contracts.ModelStore = InMemoryFlexoBackend()
    g = Graph()
    store.commit(branch="main", graph=g)
    assert isinstance(store.read_graph(branch="main"), Graph)


def test_mcp_verify_goes_through_oracle() -> None:
    from cds.mcp import tools

    assert isinstance(tools._ORACLE, contracts.InProcessOracle)
