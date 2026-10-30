"""Regression tests for integration-owned port contracts."""

import inspect

from contracts.runtime.models import Brief, CatalogQuery
from contracts.runtime.ports import CatalogPort, SessionPort


def test_catalog_query_has_optional_search_and_filters():
    q = CatalogQuery()
    assert q.search is None and q.slot is None and q.brandKind is None
    assert q.inStock is None
    assert CatalogQuery(search="dress", inStock=True).search == "dress"


def test_catalog_port_retains_pagination_and_adds_query():
    sig = inspect.signature(CatalogPort.list_variants)
    assert {"ctx", "cursor", "limit", "query"} <= set(sig.parameters)


def test_session_apply_accepts_approved_brief():
    sig = inspect.signature(SessionPort.apply)
    assert "approved_brief" in sig.parameters
    assert sig.parameters["approved_brief"].default is None


def test_brief_budget_is_integer_minor_units():
    assert "budgetMinor" in Brief.model_fields
