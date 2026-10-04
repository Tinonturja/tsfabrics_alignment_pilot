"""Bank features and coresets (section 6, Bank, Coreset, Seeding and Coreset seeds rows; deviation D5).

Bank features of one fold are written to a float32 disk array of shape (300 x 8000, 1024) in the frozen input
order: groups ascending, scenarios lexicographic, frames ascending, cells row-major. Row i belongs to bank frame
i // 8000, cell i % 8000.

Coresets use the official ApproximateGreedyCoresetSampler (fcaa92f) through its own run() method. The only change
is D5: the 1024 -> 128 random projection is applied in chunks of 100,000 rows on the GPU instead of moving all
2.4 million rows at once. The Linear layer is created exactly as in the official _reduce_features, so for a
given seed it has the official weights.
"""
import hashlib
import json
import os
import random

import numpy as np
import torch

from .detector import extract
from .official import module

FEATURES_PER_FRAME = 8000


class ChunkedApproximateGreedyCoresetSampler(module("sampler").ApproximateGreedyCoresetSampler):
    def __init__(self, percentage, device, number_of_starting_points, dimension_to_project_features_to, chunk_rows):
        super().__init__(percentage, device, number_of_starting_points, dimension_to_project_features_to)
        self.chunk_rows = chunk_rows
        self.last_indices = None

    def _reduce_features(self, features):
        if features.shape[1] == self.dimension_to_project_features_to:
            return features
        mapper = torch.nn.Linear(features.shape[1], self.dimension_to_project_features_to, bias=False)
        mapper.to(self.device)
        out = torch.empty((len(features), self.dimension_to_project_features_to), device=self.device)
        with torch.no_grad():
            for a in range(0, len(features), self.chunk_rows):
                out[a:a + self.chunk_rows] = mapper(features[a:a + self.chunk_rows].to(self.device))
        return out

    def _compute_greedy_coreset_indices(self, features):
        self.last_indices = super()._compute_greedy_coreset_indices(features)
        return self.last_indices


def seed_everything(seed):
    """Section 6: called immediately before sampler.run."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def make_sampler(dcfg, device):
    return ChunkedApproximateGreedyCoresetSampler(
        percentage=dcfg["coreset_percentage"], device=device,
        number_of_starting_points=dcfg["coreset_starting_points"],
        dimension_to_project_features_to=dcfg["coreset_projection_dim"],
        chunk_rows=dcfg["coreset_chunk_rows"])


def build(bank_features, seed, dcfg, device):
    """Run the official sampler on the (N, 1024) float32 bank features. Returns (indices int64, vectors float32)."""
    sampler = make_sampler(dcfg, device)
    seed_everything(seed)
    vectors = sampler.run(bank_features)
    indices = np.asarray(sampler.last_indices, dtype=np.int64)
    expected = int(len(bank_features) * dcfg["coreset_percentage"])
    if len(indices) != expected or vectors.shape != (expected, bank_features.shape[1]):
        raise RuntimeError(f"coreset size {len(indices)} / {vectors.shape}, expected {expected}")
    if not np.array_equal(vectors, np.asarray(bank_features[indices])):
        raise RuntimeError("coreset vectors are not the bank rows at the returned indices")
    return indices, np.ascontiguousarray(vectors, dtype=np.float32)


def index_to_source(indices, bank_rows):
    """Map coreset indices to (scenario, frame, row, col). bank_rows: the fold's [(group, scenario, frame), ...]."""
    out = []
    for i in np.asarray(indices):
        _, s, f = bank_rows[int(i) // FEATURES_PER_FRAME]
        cell = int(i) % FEATURES_PER_FRAME
        out.append((s, f, cell // 100, cell % 100))
    return out


def array_sha256(a):
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(json.dumps({"dtype": str(a.dtype), "shape": list(a.shape)}).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def save(out_dir, fold, seed, indices, vectors, meta):
    """Writes coreset_<fold>_seed<s>_{indices,vectors}.npy and a JSON record with both array hashes."""
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, f"coreset_{fold}_seed{seed}")
    np.save(stem + "_indices.npy", indices)
    np.save(stem + "_vectors.npy", vectors)
    rec = dict(meta, fold=fold, seed=seed, size=int(len(indices)), dim=int(vectors.shape[1]),
               indices_sha256=array_sha256(indices), vectors_sha256=array_sha256(vectors))
    with open(stem + ".json", "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    return rec


def load(out_dir, fold, seed, expected=None):
    """Load a saved coreset and verify its array hashes (against `expected` if given, else its own record)."""
    stem = os.path.join(out_dir, f"coreset_{fold}_seed{seed}")
    rec = expected or json.load(open(stem + ".json"))
    indices = np.load(stem + "_indices.npy")
    vectors = np.load(stem + "_vectors.npy")
    if array_sha256(indices) != rec["indices_sha256"] or array_sha256(vectors) != rec["vectors_sha256"]:
        raise ValueError(f"coreset {fold} seed {seed} does not match its recorded hashes")
    return indices, vectors


def write_bank_features(gate, net, fold, bank_rows, dcfg, device, path):
    """Bank features of one fold into a float32 disk array at `path`, in bank_rows order, batches of 4 frames.
    These features feed the coreset only (section 24); nothing here scores or summarises them."""
    n_rows = len(bank_rows) * FEATURES_PER_FRAME
    dim = dcfg["target_embed_dimension"]
    arr = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32, shape=(n_rows, dim))
    bs = dcfg["batch_size"]
    for a in range(0, len(bank_rows), bs):
        keys = [(s, f) for _, s, f in bank_rows[a:a + bs]]
        batch = gate.batch("bank", fold, keys)
        feats = extract(net, batch.images, dcfg, device)
        arr[a * FEATURES_PER_FRAME:(a + len(keys)) * FEATURES_PER_FRAME] = \
            feats.reshape(-1, dim).cpu().numpy()
    arr.flush()
    return arr
