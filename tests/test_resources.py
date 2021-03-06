#!/bin/env python3
# crun - OCI runtime written in C
#
# Copyright (C) 2017, 2018, 2019 Giuseppe Scrivano <giuseppe@scrivano.org>
# crun is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# crun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with crun.  If not, see <http://www.gnu.org/licenses/>.

import time
import json
import subprocess
import os
import shutil
import sys
from tests_utils import *


def is_cgroup_v2_unified():
    return subprocess.check_output("stat -c%T -f /sys/fs/cgroup".split()).decode("utf-8").strip() == "cgroup2fs"

def test_resources_pid_limit():
    if os.getuid() != 0:
        return 77
    conf = base_config()
    conf['linux']['resources'] = {"pids" : {"limit" : 1024}}
    add_all_namespaces(conf)

    fn = "/sys/fs/cgroup/pids/pids.max"
    if not os.path.exists("/sys/fs/cgroup/pids"):
        fn = "/sys/fs/cgroup/pids.max"
        conf['linux']['namespaces'].append({"type" : "cgroup"})

    conf['process']['args'] = ['/init', 'cat', fn]

    out, _ = run_and_get_output(conf)
    if "1024" not in out:
        return -1
    return 0

def test_resources_unified_invalid_controller():
    if not is_cgroup_v2_unified() or os.geteuid() != 0:
        return 77

    conf = base_config()
    add_all_namespaces(conf, cgroupns=True)
    conf['process']['args'] = ['/init', 'pause']

    conf['linux']['resources'] = {}
    conf['linux']['resources']['unified'] = {
            "foo.bar": "doesntmatter"
    }
    cid = None
    try:
        out, cid = run_and_get_output(conf, command='run', detach=True)
        # must raise an exception, fail if it doesn't.
        return -1
    except Exception as e:
        if 'the requested controller `foo` is not available' in e.stdout.decode("utf-8").strip():
            return 0
        return -1
    finally:
        if cid is not None:
            run_crun_command(["delete", "-f", cid])
    return 0

def test_resources_unified_invalid_key():
    if not is_cgroup_v2_unified() or os.geteuid() != 0:
        return 77

    conf = base_config()
    add_all_namespaces(conf, cgroupns=True)
    conf['process']['args'] = ['/init', 'pause']

    conf['linux']['resources'] = {}
    conf['linux']['resources']['unified'] = {
            "NOT-A-VALID-KEY": "doesntmatter"
    }
    cid = None
    try:
        out, cid = run_and_get_output(conf, command='run', detach=True)
        # must raise an exception, fail if it doesn't.
        return -1
    except Exception as e:
        if 'the specified key has not the form CONTROLLER.VALUE `NOT-A-VALID-KEY`' in e.stdout.decode("utf-8").strip():
            return 0
        return -1
    finally:
        if cid is not None:
            run_crun_command(["delete", "-f", cid])
    return 0

def test_resources_unified():
    if not is_cgroup_v2_unified() or os.geteuid() != 0:
        return 77

    conf = base_config()
    add_all_namespaces(conf, cgroupns=True)
    conf['process']['args'] = ['/init', 'pause']

    conf['linux']['resources'] = {}
    conf['linux']['resources']['unified'] = {
            "memory.high": "1073741824"
    }
    cid = None
    try:
        _, cid = run_and_get_output(conf, command='run', detach=True)
        out = run_crun_command(["exec", cid, "/init", "cat", "/sys/fs/cgroup/memory.high"])
        if "1073741824" not in out:
            return -1
    finally:
        if cid is not None:
            run_crun_command(["delete", "-f", cid])
    return 0



all_tests = {
    "resources-pid-limit" : test_resources_pid_limit,
    "resources-unified" : test_resources_unified,
    "resources-unified-invalid-controller" : test_resources_unified_invalid_controller,
    "resources-unified-invalid-key" : test_resources_unified_invalid_key,
}

if __name__ == "__main__":
    tests_main(all_tests)
