from .version_compat import Version, build_version
from .safe_import import safe_import

# Import utility functions
try:
    from .utils_helpers import check_required_packages, cleanup_routine
except ImportError:
    # If utils_helpers doesn't exist, create dummy functions
    def check_required_packages():
        pass
        
    def cleanup_routine():
        pass

__all__ = [
    'Version',  # The compatibility version class
    'build_version',  # Helper function for creating version instances
    'safe_import',  # Guarded import helper with dependency reminder
    'check_required_packages',
    'cleanup_routine'
]
