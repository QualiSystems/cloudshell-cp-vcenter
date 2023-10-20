from __future__ import annotations

import logging

from cloudshell.cp.vcenter.utils.threading import LockHandler

logger = logging.getLogger(__name__)


def test_lock_handler():
    lock_handler = LockHandler()

    with lock_handler.lock("lock1"):
        with lock_handler.lock("lock2"):
            # 2 different locks
            assert len(lock_handler._locks) == 2
