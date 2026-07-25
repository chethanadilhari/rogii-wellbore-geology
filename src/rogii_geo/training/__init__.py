"""Training-only helpers for masked residual model export.

Import submodules directly, e.g. ``rogii_geo.training.pipeline``, to avoid
circular imports with the artifact loader.
"""

from rogii_geo.training.config import TrainingConfig

__all__ = ["TrainingConfig"]
