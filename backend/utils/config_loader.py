"""Config loading utility with env var resolution"""

import yaml
import os
import re
from typing import Dict, Any


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load config from YAML file and resolve environment variables."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Resolve environment variables (e.g., ${VAR_NAME})
    config = _resolve_env_vars(config)
    
    return config


def _resolve_env_vars(obj: Any) -> Any:
    """Recursively resolve environment variables in config."""
    if isinstance(obj, dict):
        return {k: _resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Match ${VAR_NAME} pattern
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, obj)
        
        if matches:
            # Replace each match with env var value
            result = obj
            for var_name in matches:
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable {var_name} not set")
                result = result.replace(f"${{{var_name}}}", env_value)
            return result
        
        return obj
    else:
        return obj

