"""Section 6: the official code is pinned to fcaa92f. Each copied file must have the upstream git blob id."""
import hashlib
import os

import pytest

HERE = os.path.join(os.path.dirname(__file__), "..", "third_party", "patchcore")

UPSTREAM_BLOBS = {
    "LICENSE": "67db8588217f266eb561f75fae738656325deac9",
    "NOTICE": "616fc5889451895dbf9768e6787c8308c33bef22",
    "patchcore/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "patchcore/backbones.py": "3bc9448fb4e0f33bbfd2aec48b6cb99c3693847a",
    "patchcore/common.py": "eeb3c642a75577256a99a6a38b4e2c49a84c98ab",
    "patchcore/patchcore.py": "bcaa10348b8109e2bee33fc62bc7c35a71cc4de3",
    "patchcore/sampler.py": "09f57b50f92fb402838e31e101d52f2e872f48a5",
}


def git_blob_id(path):
    data = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


@pytest.mark.parametrize("rel", sorted(UPSTREAM_BLOBS))
def test_file_is_the_upstream_blob(rel):
    assert git_blob_id(os.path.join(HERE, rel)) == UPSTREAM_BLOBS[rel]


def test_no_extra_python_files():
    found = sorted(f for f in os.listdir(os.path.join(HERE, "patchcore")) if f.endswith(".py"))
    assert found == sorted(os.path.basename(k) for k in UPSTREAM_BLOBS if k.endswith(".py"))
