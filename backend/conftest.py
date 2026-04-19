from __future__ import annotations

import asyncio
import inspect

import pytest


def pytest_configure(config):
    # Keep legacy asyncio-marked tests discoverable even when pytest-asyncio
    # plugin is unavailable or incompatible with the active pytest version.
    config.addinivalue_line("markers", "asyncio: mark test as asynchronous")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    kwargs = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
        if name in pyfuncitem.funcargs
    }
    asyncio.run(test_func(**kwargs))
    return True
