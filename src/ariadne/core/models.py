"""Core data models and domain representations for Ariadne."""

from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator


class WorldGrid(BaseModel):
    """2D matrix representation of a generated game level."""
    width: int = Field(gt=0, le=500, description="Grid width in tiles")
    height: int = Field(gt=0, le=500, description="Grid height in tiles")
    cells: List[str] = Field(description="Array of strings representing rows")
    legend: Dict[str, str] = Field(description="Mapping of character symbol to semantic tile type")

    @model_validator(mode="after")
    def validate_grid_dimensions(self) -> "WorldGrid":
        if len(self.cells) != self.height:
            raise ValueError(f"Height mismatch: expected {self.height} rows, got {len(self.cells)}")
        for i, row in enumerate(self.cells):
            if len(row) != self.width:
                raise ValueError(f"Row {i} width mismatch: expected {self.width} cols, got {len(row)}")
        return self

    def get(self, x: int, y: int) -> str:
        """Get character at (x, y) coordinate. (0,0) is top-left."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return "#"

    def get_semantic(self, x: int, y: int) -> str:
        """Get semantic tile type (e.g. 'wall', 'floor', 'start') at (x, y)."""
        char = self.get(x, y)
        return self.legend.get(char, "unknown")

    def find_all(self, target: str) -> List[Tuple[int, int]]:
        """Find coordinates of all cells matching a character or semantic type."""
        coords: List[Tuple[int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                char = self.cells[y][x]
                semantic = self.legend.get(char, "")
                if char == target or semantic == target or semantic.startswith(f"{target}:"):
                    coords.append((x, y))
        return coords

    def find_first(self, target: str) -> Optional[Tuple[int, int]]:
        """Find coordinate of the first cell matching character or semantic type."""
        results = self.find_all(target)
        return results[0] if results else None

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of grid cells."""
        content = "\n".join(self.cells).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def to_ascii(self) -> str:
        """Format cells as multi-line ASCII string."""
        return "\n".join(self.cells)


@dataclass
class PrunedSubgrid:
    """Minimal Failing Map resulting from Bounding-Box Pruning."""
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    original_width: int
    original_height: int
    subgrid: WorldGrid
    rule_violated: str
    failure_description: str

    @property
    def label(self) -> str:
        return (
            f"Crop (x:{self.x_min}-{self.x_max}, y:{self.y_min}-{self.y_max}) "
            f"from {self.original_width}x{self.original_height} map"
        )


@dataclass
class SeedResult:
    """Evaluation result for one seed."""
    seed: int
    status: str  # 'pass', 'property_violation', 'timeout', 'crash', 'invalid_json'
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    violated_rule: Optional[str] = None
    grid: Optional[WorldGrid] = None
    pruned_map: Optional[PrunedSubgrid] = None

    @property
    def is_success(self) -> bool:
        return self.status == "pass"


@dataclass
class RunSummary:
    """Aggregated statistics across an evaluation run."""
    total_seeds: int = 0
    passed_seeds: int = 0
    failed_seeds: int = 0
    timeouts: int = 0
    crashes: int = 0
    invalid_jsons: int = 0
    property_violations: int = 0
    vault_replayed: int = 0
    vault_regressions: int = 0
    duration_seconds: float = 0.0
    failures: List[SeedResult] = field(default_factory=list)

    @property
    def solvability_ratio(self) -> float:
        if self.total_seeds == 0:
            return 1.0
        return self.passed_seeds / self.total_seeds
