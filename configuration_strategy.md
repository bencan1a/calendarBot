# CalendarBot Configuration Strategy for Optional Resource-Intensive Features

## Overview

This configuration strategy enables selective activation of resource-intensive features based on deployment constraints, allowing CalendarBot to operate efficiently across different environments from Pi Zero 2W (512MB RAM) to full-featured deployments.

## Architecture Principles

### 1. Three-Tier Configuration System

```
BUILD-TIME CONFIG    →  Feature compilation inclusion/exclusion
DEPLOYMENT CONFIG    →  Environment-specific feature activation  
RUNTIME CONFIG       →  Dynamic feature toggling
```

### 2. Configuration Hierarchy

```python
# Priority order (lowest to highest)
1. Default settings (hardcoded)
2. Build-time flags (compile-time)
3. Environment variables
4. Configuration file (config.yaml)
5. Runtime API calls
```

## Feature Flag Architecture

### 1. Core Configuration Model

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any

class DeploymentMode(Enum):
    MINIMAL = "minimal"      # Pi Zero, resource-constrained
    STANDARD = "standard"    # Standard Pi/desktop
    FULL = "full"           # Development/full-featured

class FeatureConfig(BaseModel):
    """Individual feature configuration"""
    enabled: bool = True
    mode: Optional[str] = None
    parameters: Dict[str, Any] = {}
    
class CalendarBotConfig(BaseModel):
    """Master configuration for feature flags"""
    
    # Deployment configuration
    deployment_mode: DeploymentMode = DeploymentMode.STANDARD
    
    # Performance monitoring features
    performance_monitoring: FeatureConfig = FeatureConfig(enabled=True)
    memory_monitoring: FeatureConfig = FeatureConfig(enabled=True)
    cache_performance_tracking: FeatureConfig = FeatureConfig(enabled=True)
    
    # Caching system features
    dual_cache_storage: FeatureConfig = FeatureConfig(enabled=False)
    cache_wal_mode: FeatureConfig = FeatureConfig(enabled=True)
    cache_advanced_indexes: FeatureConfig = FeatureConfig(enabled=True)
    
    # Development/debugging features
    debug_utilities: FeatureConfig = FeatureConfig(enabled=False)
    validation_framework: FeatureConfig = FeatureConfig(
        enabled=True, 
        mode="standard"
    )
    
    # Web server optimizations
    static_asset_caching: FeatureConfig = FeatureConfig(enabled=True)
    static_asset_preloading: FeatureConfig = FeatureConfig(enabled=False)
    
    # Browser management
    browser_memory_monitoring: FeatureConfig = FeatureConfig(enabled=True)
    browser_health_checks: FeatureConfig = FeatureConfig(enabled=True)
    
    # Layout and theming
    dynamic_layout_discovery: FeatureConfig = FeatureConfig(enabled=False)
    theme_hot_reloading: FeatureConfig = FeatureConfig(enabled=False)
```

### 2. Deployment Mode Presets

```python
DEPLOYMENT_PRESETS = {
    DeploymentMode.MINIMAL: {
        "performance_monitoring": FeatureConfig(enabled=False),
        "memory_monitoring": FeatureConfig(enabled=False),
        "cache_performance_tracking": FeatureConfig(enabled=False),
        "dual_cache_storage": FeatureConfig(enabled=False),
        "cache_wal_mode": FeatureConfig(enabled=False),
        "cache_advanced_indexes": FeatureConfig(enabled=False),
        "debug_utilities": FeatureConfig(enabled=False),
        "validation_framework": FeatureConfig(enabled=True, mode="basic"),
        "static_asset_caching": FeatureConfig(enabled=True),
        "static_asset_preloading": FeatureConfig(enabled=False),
        "browser_memory_monitoring": FeatureConfig(
            enabled=True, 
            parameters={"memory_limit_mb": 64, "check_interval": 30}
        ),
        "browser_health_checks": FeatureConfig(enabled=False),
        "dynamic_layout_discovery": FeatureConfig(enabled=False),
        "theme_hot_reloading": FeatureConfig(enabled=False),
    },
    
    DeploymentMode.STANDARD: {
        "performance_monitoring": FeatureConfig(enabled=True),
        "memory_monitoring": FeatureConfig(enabled=True),
        "cache_performance_tracking": FeatureConfig(enabled=False),
        "dual_cache_storage": FeatureConfig(enabled=False),
        "cache_wal_mode": FeatureConfig(enabled=True),
        "cache_advanced_indexes": FeatureConfig(enabled=True),
        "debug_utilities": FeatureConfig(enabled=False),
        "validation_framework": FeatureConfig(enabled=True, mode="standard"),
        "static_asset_caching": FeatureConfig(enabled=True),
        "static_asset_preloading": FeatureConfig(enabled=True),
        "browser_memory_monitoring": FeatureConfig(
            enabled=True,
            parameters={"memory_limit_mb": 128, "check_interval": 60}
        ),
        "browser_health_checks": FeatureConfig(enabled=True),
        "dynamic_layout_discovery": FeatureConfig(enabled=False),
        "theme_hot_reloading": FeatureConfig(enabled=False),
    },
    
    DeploymentMode.FULL: {
        "performance_monitoring": FeatureConfig(enabled=True),
        "memory_monitoring": FeatureConfig(enabled=True),
        "cache_performance_tracking": FeatureConfig(enabled=True),
        "dual_cache_storage": FeatureConfig(enabled=True),
        "cache_wal_mode": FeatureConfig(enabled=True),
        "cache_advanced_indexes": FeatureConfig(enabled=True),
        "debug_utilities": FeatureConfig(enabled=True),
        "validation_framework": FeatureConfig(enabled=True, mode="comprehensive"),
        "static_asset_caching": FeatureConfig(enabled=True),
        "static_asset_preloading": FeatureConfig(enabled=True),
        "browser_memory_monitoring": FeatureConfig(
            enabled=True,
            parameters={"memory_limit_mb": 256, "check_interval": 120}
        ),
        "browser_health_checks": FeatureConfig(enabled=True),
        "dynamic_layout_discovery": FeatureConfig(enabled=True),
        "theme_hot_reloading": FeatureConfig(enabled=True),
    }
}
```

## Build System Integration

### 1. Conditional Compilation Strategy

```python
# build_config.py
import os
from typing import List

class BuildConfig:
    """Build-time feature flags for compilation exclusion"""
    
    def __init__(self, deployment_mode: str = "standard"):
        self.deployment_mode = deployment_mode
        
    def get_excluded_modules(self) -> List[str]:
        """Get modules to exclude from build based on deployment mode"""
        exclusions = []
        
        if self.deployment_mode == "minimal":
            exclusions.extend([
                "calendarbot.monitoring.performance",
                "calendarbot.monitoring.benchmarks", 
                "calendarbot.cache.raw_storage",
                "calendarbot.validation.comprehensive",
                "calendarbot.web.debug_utilities",
                "calendarbot.layout.dynamic_discovery",
            ])
            
        elif self.deployment_mode == "standard":
            exclusions.extend([
                "calendarbot.monitoring.benchmarks",
                "calendarbot.cache.raw_storage", 
                "calendarbot.web.debug_utilities",
                "calendarbot.layout.dynamic_discovery",
            ])
            
        return exclusions
        
    def get_build_flags(self) -> Dict[str, bool]:
        """Get preprocessor flags for conditional compilation"""
        return {
            "ENABLE_PERFORMANCE_MONITORING": self.deployment_mode != "minimal",
            "ENABLE_DEBUG_UTILITIES": self.deployment_mode == "full",
            "ENABLE_RAW_CACHE": self.deployment_mode == "full",
            "ENABLE_VALIDATION_COMPREHENSIVE": self.deployment_mode == "full",
            "ENABLE_BROWSER_HEALTH_CHECKS": self.deployment_mode != "minimal",
        }
```

### 2. Webpack Configuration for Frontend

```javascript
// webpack.config.js
const path = require('path');

module.exports = (env) => {
    const deploymentMode = env.deployment || 'standard';
    
    const config = {
        entry: './src/index.js',
        mode: env.production ? 'production' : 'development',
        plugins: [],
    };
    
    // Conditional feature exclusion
    const definePlugin = new webpack.DefinePlugin({
        'process.env.DEPLOYMENT_MODE': JSON.stringify(deploymentMode),
        'ENABLE_DEBUG_UTILITIES': deploymentMode === 'full',
        'ENABLE_PERFORMANCE_TRACKING': deploymentMode !== 'minimal',
    });
    
    config.plugins.push(definePlugin);
    
    // Module exclusions for minimal builds
    if (deploymentMode === 'minimal') {
        config.resolve = {
            alias: {
                './debug-utilities': path.resolve(__dirname, 'src/stubs/debug-stub.js'),
                './performance-monitor': path.resolve(__dirname, 'src/stubs/perf-stub.js'),
            }
        };
    }
    
    return config;
};
```

## Runtime Configuration Management

### 1. Configuration Loader

```python
# config/loader.py
import os
import yaml
from pathlib import Path
from typing import Optional

class ConfigurationLoader:
    """Load and merge configuration from multiple sources"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".calendarbot" / "config.yaml"
        
    def load_config(self) -> CalendarBotConfig:
        """Load configuration with precedence hierarchy"""
        
        # 1. Start with deployment mode preset
        deployment_mode = self._get_deployment_mode()
        base_config = DEPLOYMENT_PRESETS.get(deployment_mode, {})
        
        # 2. Load from configuration file
        file_config = self._load_config_file()
        
        # 3. Override with environment variables
        env_config = self._load_environment_config()
        
        # 4. Merge configurations
        merged_config = self._merge_configs(base_config, file_config, env_config)
        
        return CalendarBotConfig(**merged_config)
        
    def _get_deployment_mode(self) -> DeploymentMode:
        """Determine deployment mode from environment or file"""
        mode_str = os.getenv("CALENDARBOT_DEPLOYMENT_MODE")
        if not mode_str and self.config_path.exists():
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
                mode_str = config.get("deployment_mode")
                
        try:
            return DeploymentMode(mode_str) if mode_str else DeploymentMode.STANDARD
        except ValueError:
            return DeploymentMode.STANDARD
            
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            return {}
            
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}
            
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # Map environment variables to config keys
        env_mappings = {
            "CALENDARBOT_PERFORMANCE_MONITORING": "performance_monitoring.enabled",
            "CALENDARBOT_DEBUG_UTILITIES": "debug_utilities.enabled", 
            "CALENDARBOT_CACHE_WAL_MODE": "cache_wal_mode.enabled",
            "CALENDARBOT_BROWSER_MEMORY_LIMIT": "browser_memory_monitoring.parameters.memory_limit_mb",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(env_config, config_path, self._parse_env_value(value))
                
        return env_config
```

### 2. Feature Flag Decorator Pattern

```python
# decorators.py
from functools import wraps
from typing import Callable, Any

def feature_flag(flag_path: str, fallback_return: Any = None):
    """Decorator to conditionally execute functions based on feature flags"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = get_current_config()  # Global config accessor
            
            # Parse nested flag path (e.g., "performance_monitoring.enabled")
            flag_value = get_nested_value(config, flag_path)
            
            if flag_value:
                return func(*args, **kwargs)
            else:
                return fallback_return
                
        return wrapper
    return decorator

# Usage examples
@feature_flag("performance_monitoring.enabled")
def log_performance_metric(metric_name: str, value: float) -> None:
    """Log performance metric if monitoring is enabled"""
    performance_logger.log_metric(metric_name, value)

@feature_flag("debug_utilities.enabled", fallback_return=[])
def get_debug_info() -> List[Dict[str, Any]]:
    """Return debug information if debugging is enabled"""
    return collect_debug_information()
```

## Implementation Strategy

### 1. Migration Phases

**Phase 1: Configuration Infrastructure (Week 1-2)**
- Implement configuration model and loader
- Add feature flag decorators
- Create deployment mode presets
- Update build system for conditional compilation

**Phase 2: Feature Flag Integration (Week 3-4)**
- Add feature flags to performance monitoring
- Implement conditional cache system features
- Update validation framework with modes
- Add browser memory management configuration

**Phase 3: Build System Optimization (Week 5-6)**
- Implement frontend build exclusions
- Create deployment-specific Docker images
- Add automated build pipeline for different modes
- Test resource usage across deployment modes

**Phase 4: Runtime Configuration (Week 7-8)**
- Add configuration hot-reloading
- Implement configuration validation
- Add configuration management API endpoints
- Create configuration migration tools

### 2. Configuration File Examples

**Minimal Deployment (config.yaml)**
```yaml
deployment_mode: minimal

performance_monitoring:
  enabled: false

cache_wal_mode:
  enabled: false

browser_memory_monitoring:
  enabled: true
  parameters:
    memory_limit_mb: 64
    warning_threshold: 0.8
    critical_threshold: 0.95
    check_interval: 30

validation_framework:
  enabled: true
  mode: basic
  
static_asset_caching:
  enabled: true
  parameters:
    max_cache_size_mb: 10
    cache_duration_hours: 24
```

**Standard Deployment (config.yaml)**
```yaml
deployment_mode: standard

performance_monitoring:
  enabled: true
  parameters:
    log_interval_seconds: 300
    metrics_retention_hours: 24

cache_wal_mode:
  enabled: true

browser_memory_monitoring:
  enabled: true
  parameters:
    memory_limit_mb: 128
    warning_threshold: 0.85
    critical_threshold: 0.95
    check_interval: 60

validation_framework:
  enabled: true
  mode: standard
```

### 3. Environment Variable Override Examples

```bash
# Minimal resource deployment
export CALENDARBOT_DEPLOYMENT_MODE=minimal
export CALENDARBOT_PERFORMANCE_MONITORING=false
export CALENDARBOT_BROWSER_MEMORY_LIMIT=48

# Standard deployment with custom settings
export CALENDARBOT_DEPLOYMENT_MODE=standard
export CALENDARBOT_CACHE_WAL_MODE=true
export CALENDARBOT_DEBUG_UTILITIES=false
```

## Monitoring and Validation

### 1. Configuration Validation

```python
def validate_deployment_config(config: CalendarBotConfig) -> List[str]:
    """Validate configuration for consistency and resource constraints"""
    warnings = []
    
    # Resource constraint validations
    if config.deployment_mode == DeploymentMode.MINIMAL:
        if config.performance_monitoring.enabled:
            warnings.append("Performance monitoring enabled in minimal mode may impact performance")
            
        memory_limit = config.browser_memory_monitoring.parameters.get("memory_limit_mb", 128)
        if memory_limit > 64:
            warnings.append(f"Browser memory limit {memory_limit}MB may be too high for minimal deployment")
            
    return warnings
```

### 2. Resource Usage Monitoring

```python
@feature_flag("performance_monitoring.enabled")
def monitor_configuration_impact() -> Dict[str, Any]:
    """Monitor resource impact of enabled features"""
    return {
        "memory_usage_mb": get_process_memory_usage(),
        "cpu_usage_percent": get_process_cpu_usage(), 
        "enabled_features": get_enabled_features_list(),
        "estimated_overhead_mb": calculate_feature_overhead(),
    }
```

## Success Metrics

**Resource Usage Targets by Deployment Mode:**

| Mode | Max Memory | Max CPU | Bundle Size | Startup Time |
|------|------------|---------|-------------|--------------|
| Minimal | 400MB | 15% | <2MB | <10s |
| Standard | 600MB | 25% | <5MB | <15s |
| Full | 1GB | 40% | <10MB | <30s |

**Configuration Management Goals:**
- Zero-downtime configuration updates
- <1s configuration reload time
- 100% backward compatibility for 2 major versions
- Automatic configuration migration between versions