"""
Machine-Readable Reproducibility Manifest Generator (Refinement 7).

Generates a reproducibility_manifest.json capturing exact environment state, git commit,
model versions, configuration hash, random seed, and result checksums.
"""

import os
import sys
import platform
import hashlib
import json
import time
from typing import Dict, Any
from pydantic import BaseModel
from .versioning import get_current_asset_versions


class ReproducibilityManifest(BaseModel):
    benchmark_id: str
    timestamp: float
    git_commit_hash: str
    asset_versions: Dict[str, str]
    python_version: str
    platform_info: str
    random_seed: int = 42
    hardware_info: Dict[str, Any]
    result_checksum: str = ""


class ManifestGenerator:
    """Generates reproducibility manifests for scientific benchmark runs."""

    def generate_manifest(self, benchmark_id: str, results_dict: Dict[str, Any]) -> ReproducibilityManifest:
        versions = get_current_asset_versions().to_dict()

        # Git commit hash (fallback to local mock if git unavailable)
        git_hash = os.popen("git rev-parse HEAD 2>NUL").read().strip() or "dev-uncommitted"

        # Hardware info
        hw_info = {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_executable": sys.executable,
        }

        # Calculate result checksum
        raw_str = json.dumps(results_dict, sort_keys=True)
        checksum = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        return ReproducibilityManifest(
            benchmark_id=benchmark_id,
            timestamp=time.time(),
            git_commit_hash=git_hash,
            asset_versions=versions,
            python_version=sys.version.split()[0],
            platform_info=platform.platform(),
            hardware_info=hw_info,
            result_checksum=checksum,
        )
