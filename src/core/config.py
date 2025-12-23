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
    max_model_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="模型token上限（用于裁剪）/ Model token cap for clamping"
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

    @property
    def effective_max_tokens(self) -> int:
        """获取裁剪后的最大token数 / Get clamped max tokens"""
        cap = self.max_model_tokens or self._infer_model_token_cap()
        if cap:
            return min(self.max_tokens, cap)
        return self.max_tokens

    def _infer_model_token_cap(self) -> Optional[int]:
        """
        根据模型名称推断token上限
        """
        name = (self.effective_model_name or "").lower()
        if "128k" in name:
            return 131072
        if "64k" in name:
            return 65536
        if "32k" in name:
            return 32768
        if "16k" in name:
            return 16384
        if "8k" in name:
            return 8192
        return None


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
    max_parallel_tools: int = Field(
        default=4,
        gt=0,
        description="并行工具执行上限 / Max parallel tool executions"
    )


class ShellToolConfig(BaseModel):
    """Shell工具配置 / Shell Tool Configuration"""
    enabled: bool = Field(default=True, description="是否启用 / Enabled")
    policy: str = Field(
        default="whitelist",
        description="安全策略（allow_all/deny_all/whitelist）/ Security policy"
    )
    whitelist: List[str] = Field(
        default=["echo", "ls", "dir", "cat", "type", "pwd", "cd", "head", "tail", "grep", "find", "where", "which", "python", "pip", "node", "npm", "git"],
        description="白名单命令前缀 / Whitelist command prefixes"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="执行超时（秒）/ Execution timeout (seconds)"
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
    shell_tool: ShellToolConfig = Field(default_factory=ShellToolConfig)
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
    max_context_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="上下文最大token数（估算）/ Maximum context tokens (estimated)"
    )
    system_token_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="系统上下文预算占比 / System context budget ratio"
    )
    file_context_token_ratio: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="文件上下文预算占比 / File context budget ratio"
    )
    history_token_ratio: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="对话历史预算占比 / History context budget ratio"
    )
    file_context_chunk_size: int = Field(
        default=800,
        gt=0,
        description="文件分块大小（字符数）/ File chunk size (chars)"
    )
    file_context_max_chunks_per_file: int = Field(
        default=2,
        gt=0,
        description="每个文件最大分块数 / Max chunks per file"
    )
    file_context_min_score: int = Field(
        default=1,
        ge=0,
        description="分块最小相关性分数 / Minimum chunk relevance score"
    )
    file_context_query_messages: int = Field(
        default=3,
        gt=0,
        description="用于检索的最近用户消息数 / Recent user messages for retrieval"
    )
    type: str = Field(default="buffer", description="记忆类型 / Memory type")
    summary_keep_last_n: int = Field(
        default=20,
        gt=0,
        description="摘要模式保留的最近消息数 / Keep last N messages in summary mode"
    )
    summary_max_chars: int = Field(
        default=4000,
        gt=0,
        description="摘要最大字符数 / Maximum summary characters"
    )


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
