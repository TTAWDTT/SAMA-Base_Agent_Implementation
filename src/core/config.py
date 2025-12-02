# ==============================================================================
# 配置管理模块 / Configuration Management Module
# ==============================================================================
# 负责加载和管理项目配置
# Responsible for loading and managing project configuration
# ==============================================================================

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """模型配置 / Model Configuration"""
    api_key: str = Field(default="", description="API密钥 / API Key")
    base_url: str = Field(
        default="https://api.moonshot.cn/v1",
        description="API基础URL / API Base URL"
    )
    model_name: str = Field(
        default="moonshot-v1-128k",
        description="模型名称 / Model Name"
    )
    main_model_name: Optional[str] = Field(
        default=None,
        description="主模型名称 / Main Model Name"
    )
    sub_model_name: Optional[str] = Field(
        default=None,
        description="子模型名称 / Sub Model Name"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="温度参数 / Temperature"
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="最大token数 / Maximum tokens"
    )
    timeout: int = Field(
        default=120,
        gt=0,
        description="请求超时（秒）/ Request timeout (seconds)"
    )
    
    @property
    def effective_model_name(self) -> str:
        """获取有效的模型名称 / Get effective model name"""
        return self.main_model_name or self.model_name


class AgentConfig(BaseModel):
    """Agent配置 / Agent Configuration"""
    max_iterations: int = Field(
        default=10,
        gt=0,
        description="最大迭代次数 / Maximum iterations"
    )
    verbose: bool = Field(
        default=True,
        description="是否启用详细日志 / Enable verbose logging"
    )
    prompt_language: str = Field(
        default="zh",
        description="提示词语言 / Prompt language"
    )
    workspace: str = Field(
        default="./workspace",
        description="Agent工作区目录 / Agent workspace directory"
    )


class FileToolConfig(BaseModel):
    """文件工具配置 / File Tool Configuration"""
    enabled: bool = Field(default=True, description="是否启用 / Enabled")
    allowed_directories: List[str] = Field(
        default=["./workspace", "./outputs"],
        description="允许访问的目录 / Allowed directories"
    )


class CodeExecutorConfig(BaseModel):
    """代码执行工具配置 / Code Executor Configuration"""
    enabled: bool = Field(default=True, description="是否启用 / Enabled")
    allowed_languages: List[str] = Field(
        default=["python", "javascript"],
        description="允许的编程语言 / Allowed programming languages"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="执行超时（秒）/ Execution timeout (seconds)"
    )


class SearchToolConfig(BaseModel):
    """搜索工具配置 / Search Tool Configuration"""
    enabled: bool = Field(default=False, description="是否启用 / Enabled")
    api_key: str = Field(default="", description="搜索API密钥 / Search API Key")
    engine: str = Field(default="google", description="搜索引擎 / Search engine")


class ToolsConfig(BaseModel):
    """工具配置 / Tools Configuration"""
    file_tool: FileToolConfig = Field(default_factory=FileToolConfig)
    code_executor: CodeExecutorConfig = Field(default_factory=CodeExecutorConfig)
    search_tool: SearchToolConfig = Field(default_factory=SearchToolConfig)


class LoggingConfig(BaseModel):
    """日志配置 / Logging Configuration"""
    level: str = Field(default="INFO", description="日志级别 / Log level")
    file_path: str = Field(
        default="outputs/logs/agent.log",
        description="日志文件路径 / Log file path"
    )
    console_output: bool = Field(
        default=True,
        description="是否输出到控制台 / Output to console"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式 / Log format"
    )


class MemoryConfig(BaseModel):
    """内存配置 / Memory Configuration"""
    enabled: bool = Field(default=True, description="是否启用对话记忆 / Enable memory")
    max_entries: int = Field(
        default=100,
        gt=0,
        description="最大记忆条数 / Maximum memory entries"
    )
    type: str = Field(default="buffer", description="记忆类型 / Memory type")


class Config(BaseModel):
    """
    完整配置类 / Complete Configuration Class
    
    统一管理所有配置项，支持从YAML文件加载
    Unified management of all configuration items, supports loading from YAML files
    """
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)


def find_project_root() -> Path:
    """
    查找项目根目录 / Find project root directory
    
    通过查找config.yaml或.git目录来确定项目根目录
    Determines project root by looking for config.yaml or .git directory
    
    Returns:
        Path: 项目根目录路径 / Project root directory path
    """
    current_path = Path.cwd()
    
    # 向上查找包含config.yaml的目录
    # Search upward for directory containing config.yaml
    for parent in [current_path] + list(current_path.parents):
        if (parent / "config.yaml").exists():
            return parent
        if (parent / ".git").exists():
            return parent
    
    return current_path


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件 / Load configuration file
    
    优先级 / Priority:
    1. 指定的配置文件路径 / Specified config file path
    2. config.local.yaml（本地配置）/ config.local.yaml (local config)
    3. config.yaml（默认配置）/ config.yaml (default config)
    
    Args:
        config_path: 配置文件路径 / Configuration file path
        
    Returns:
        Config: 配置对象 / Configuration object
    """
    project_root = find_project_root()
    
    # 确定配置文件路径 / Determine config file path
    if config_path:
        config_file = Path(config_path)
    else:
        # 优先使用本地配置 / Prefer local config
        local_config = project_root / "config.local.yaml"
        default_config = project_root / "config.yaml"
        
        if local_config.exists():
            config_file = local_config
        elif default_config.exists():
            config_file = default_config
        else:
            # 返回默认配置 / Return default config
            return Config()
    
    # 读取配置文件 / Read config file
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        return Config(**config_data)
    
    return Config()


def get_api_key_from_env() -> Optional[str]:
    """
    从环境变量获取API密钥 / Get API key from environment variable
    
    支持多种环境变量名 / Supports multiple environment variable names:
    - OPENAI_API_KEY
    - KIMI_API_KEY
    - MOONSHOT_API_KEY
    - API_KEY
    
    Returns:
        Optional[str]: API密钥 / API key
    """
    env_vars = ["OPENAI_API_KEY", "KIMI_API_KEY", "MOONSHOT_API_KEY", "API_KEY"]
    for var in env_vars:
        api_key = os.getenv(var)
        if api_key:
            return api_key
    return None


# 全局配置实例 / Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例 / Get global configuration instance
    
    使用单例模式，确保配置只加载一次
    Uses singleton pattern to ensure config is loaded only once
    
    Returns:
        Config: 配置对象 / Configuration object
    """
    global _config
    if _config is None:
        _config = load_config()
        
        # 如果配置文件中没有API密钥，尝试从环境变量获取
        # If no API key in config file, try to get from environment variable
        if not _config.model.api_key or _config.model.api_key == "your-api-key-here":
            env_api_key = get_api_key_from_env()
            if env_api_key:
                _config.model.api_key = env_api_key
    
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """
    重新加载配置 / Reload configuration
    
    Args:
        config_path: 配置文件路径 / Configuration file path
        
    Returns:
        Config: 配置对象 / Configuration object
    """
    global _config
    _config = load_config(config_path)
    
    # 如果配置文件中没有API密钥，尝试从环境变量获取
    # If no API key in config file, try to get from environment variable
    if not _config.model.api_key or _config.model.api_key == "your-api-key-here":
        env_api_key = get_api_key_from_env()
        if env_api_key:
            _config.model.api_key = env_api_key
    
    return _config
