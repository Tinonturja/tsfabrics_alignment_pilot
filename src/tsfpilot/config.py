"""Configuration loader (all sections). Refuses unknown or missing keys so no constant can hide in code."""
import hashlib
import os

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT = os.path.join(REPO, "configs", "pilot_v1_2_1.yaml")

REQUIRED = {
    "spec": {"preregistration_sha256", "amendment_v1_2_1_sha256"},
    "data": {"frame_width", "frame_height", "normal_labels", "cutline_anchor_labels", "passes_csv", "clusters_csv",
             "bank_audit_csv", "forensic_summary_csv", "label_override"},
    "periods": None,
    "folds": None,
    "bank": {"frames_per_fold", "per_group_total", "margin_extra", "dark_spacing"},
    "detector": {"backbone", "weights", "layers", "patchsize", "pretrain_embed_dimension", "target_embed_dimension",
                 "imagenet_mean", "imagenet_std", "map_shape", "coreset_percentage", "coreset_starting_points",
                 "coreset_projection_dim", "coreset_chunk_rows", "coreset_seeds", "query_chunk", "batch_size",
                 "patchcore_commit"},
    "motion": {"crop_rows", "std_min", "max_abs_dx", "max_abs_dy", "consistency_min_history", "consistency_window",
               "consistency_abs", "consistency_rel", "tau_r_grid_step", "tau_r_min_pairs", "tau_r_min_consistent",
               "hold_frames", "cell_px", "motion_unknown_max_fraction", "oracle_halfwidth", "oracle_min_values"},
    "windows": {"k_min", "k_max", "k_initial", "k_stopped", "reliable_for_k", "median_window", "span_px"},
    "passes": {"grace_max"},
    "events": {"merge_gap", "duration_cap", "fa_per"},
    "metrics": {"p1_recall_num", "p1_recall_den", "p1_cap", "p2_fa", "p3_fmax", "q9_places"},
    "bootstrap": {"replicates", "seed", "phase_bin", "block_length", "ci_low_pct", "ci_high_pct"},
    "chance": {"n_shifts", "seed_base", "offset_support", "collapse_k"},
    "criteria": {"c0a_num", "c0a_den", "band", "c1_pass", "c1_fail", "c2_min", "c4_pass_share", "c4_fail_share"},
    "decomposition": {"null_row_offset", "floor_fraction", "diffuse", "camera", "persistent", "separation",
                      "transient", "min_path"},
}
FOLD_KEYS = {"index", "test", "expected", "validation", "bank_groups", "bank_quota", "tau_r_groups"}


class ConfigError(ValueError):
    pass


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(path=DEFAULT):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    unknown = set(cfg) - set(REQUIRED)
    missing = set(REQUIRED) - set(cfg)
    if unknown or missing:
        raise ConfigError(f"top-level keys: unknown {sorted(unknown)}, missing {sorted(missing)}")
    for sec, keys in REQUIRED.items():
        if keys is None:
            continue
        got = set(cfg[sec])
        if got != keys:
            raise ConfigError(f"[{sec}] unknown {sorted(got - keys)}, missing {sorted(keys - got)}")
    for name, fold in cfg["folds"].items():
        if set(fold) != FOLD_KEYS:
            raise ConfigError(f"fold {name}: keys {sorted(set(fold) ^ FOLD_KEYS)} differ")
    if cfg["chance"]["offset_support"] != "full_cyclic_group":
        raise ConfigError("v1.2.1 requires chance.offset_support = full_cyclic_group")
    cfg["_path"] = os.path.abspath(path)
    cfg["_sha256"] = file_sha256(path)
    return cfg


def repo_path(rel):
    return os.path.join(REPO, rel)
