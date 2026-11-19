"""Load optional drivers only when an integration test requests one."""

from importlib import import_module

import pytest


@pytest.fixture
def psycopg():
    return import_module("psycopg")


@pytest.fixture
def pymysql():
    return import_module("pymysql")


@pytest.fixture
def pymssql():
    return import_module("pymssql")
