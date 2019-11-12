import pprint
import os
from latigo.utils import merge, load_config, load_yaml, save_yaml

# TODO: Actually manage this
writable_working_dir="/tmp/"

def merge_test_worker(skip, expected):
    # fmt: off
    a={
        'both':'AAAA',
        'only_a':'AAAA',
        'both_none':None,
        'only_a_none':None,
    }
    b={
        'both':'BBBB',
        'only_b':'BBBB',
        'both_none':None,
        'only_b_none':None,
    }
    # fmt: on
    print("a:")
    print(pprint.pformat(a))
    print("b:")
    print(pprint.pformat(b))
    merge(a, b, skip)
    print("res:")
    print(pprint.pformat(b))
    assert b == expected


def test_merge_with_skip_none():
    # fmt: off
    expected={
        'both':'AAAA',
        'only_a':'AAAA',
        'only_b':'BBBB',
        'both_none':None,
        'only_b_none':None,
    }
    # fmt: on
    merge_test_worker(True, expected)
    return True


def test_merge_without_skip_none():
    # fmt: off
    expected={
        'both':'AAAA',
        'only_a':'AAAA',
        'only_b':'BBBB',
        'both_none':None,
        'only_a_none':None,
        'only_b_none':None,
    }
    # fmt: on
    merge_test_worker(False, expected)
    return True


def test_save_load_yaml():
    config_filename = writable_working_dir + "test_config_save_load.yaml"
    # fmt: off
    original_config={
        'both':'AAAA',
        'only_a':'AAAA',
        'both_none':None,
        'only_a_none':None,
    }
    # fmt: on
    save_yaml(config_filename, original_config, True)
    assert os.path.exists(config_filename)
    config, failure = load_yaml(config_filename, True)
    if os.path.exists(config_filename):
        os.remove(config_filename)
    assert failure == None
    assert original_config == config


def test_load_config():
    config_filename = writable_working_dir + "test_config_load_config.yaml"
    # fmt: off
    original_config={
        'both':'FILE',
        'only_file':'FILE',
        'both_none':None,
        'only_file_none':None,
    }
    overlay_config={
        'both':'OVERLAY',
        'only_overlay':'OVERLAY',
        'both_none':None,
        'only_overlay_none':None,
    }
    expected={
        'both': 'OVERLAY',
        'both_none': None,
        'only_file': 'FILE',
        'only_file_none': None,
        'only_overlay': 'OVERLAY',
    }
    # fmt: on
    save_yaml(config_filename, original_config)
    config = load_config(config_filename, overlay_config, True)
    print("loaded config:")
    print(pprint.pformat(config))
    if os.path.exists(config_filename):
        os.remove(config_filename)
    assert config == expected
