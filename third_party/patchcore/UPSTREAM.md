# Official PatchCore code, pinned

Source: https://github.com/amazon-science/patchcore-inspection, commit
`fcaa92f124fb1ad74a7acf56726decd4b27cbcad` (2023-03-06), Apache License 2.0 (`LICENSE`, `NOTICE`).

The files below are byte-for-byte copies; none is edited. `tests/test_third_party_pin.py` recomputes each git blob id
and compares it with the id of the same path in the upstream tree at that commit.

| Here | Upstream path | Git blob id at fcaa92f |
|---|---|---|
| `LICENSE` | `LICENSE` | `67db8588217f266eb561f75fae738656325deac9` |
| `NOTICE` | `NOTICE` | `616fc5889451895dbf9768e6787c8308c33bef22` |
| `patchcore/__init__.py` | `src/patchcore/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` |
| `patchcore/backbones.py` | `src/patchcore/backbones.py` | `3bc9448fb4e0f33bbfd2aec48b6cb99c3693847a` |
| `patchcore/common.py` | `src/patchcore/common.py` | `eeb3c642a75577256a99a6a38b4e2c49a84c98ab` |
| `patchcore/patchcore.py` | `src/patchcore/patchcore.py` | `bcaa10348b8109e2bee33fc62bc7c35a71cc4de3` |
| `patchcore/sampler.py` | `src/patchcore/sampler.py` | `09f57b50f92fb402838e31e101d52f2e872f48a5` |

How each is used (section 6 of the preregistration):

- `sampler.py`: `ApproximateGreedyCoresetSampler` builds every coreset. The pipeline subclasses it and replaces only
  `_reduce_features` with the row-chunked projection (deviation D5).
- `common.py`, `patchcore.py`, `backbones.py`: imported only by the AT-02 reference, which runs the official
  `PatchCore._embed` on the same frames. `common.py` imports `faiss` and `backbones.py` imports `timm` at import
  time, so both packages must be installed for AT-02; neither is used by the pipeline.

Why a copy and not a git submodule (DL-0013, audit item F6): the repository travels as `git am` patches and as a
Kaggle dataset upload, and neither carries submodule contents.
