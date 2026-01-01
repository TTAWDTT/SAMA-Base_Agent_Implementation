# ==============================================================================
# 配置管理模块
# ==============================================================================
# 负责加载和管理项目配置
# ==============================================================================

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """模型配置"""
    api_key: str = Field(default="", description="API密钥")
    base_url: str = Field(
        default="https://api.moonshot.cn/v1",
        description="API基础URL"
    )
    model_name: str = Field(
        default="moonshot-v1-128k",
        description="模型名称"
    )
    main_model_name: Optional[str] = Field(
        default=None,
        description="主模型名称"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="温度参数"
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="最大token数"
    )
    max_model_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="模型token上限（用于裁剪）"
    )
    timeout: int = Field(
        default=120,
        gt=0,
        description="请求超时（秒）"
    )
    
    @property
    def effective_model_name(self) -> str:
        """获取有效的模型名称"""
        return self.main_model_name or self.model_name

    @property
    def effective_max_tokens(self) -> int:
        """获取裁剪后的最大token数"""
        cap = self.max_model_tokens or self._infer_model_token_cap()
        if cap:
            return min(self.max_tokens, cap)
        return self.max_tokens

    def _infer_model_token_cap(self) -> Optional[int]:
        """根据模型名称推断token上限"""
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
    """Agent配置"""
    max_iterations: int = Field(
        default=10,
        gt=0,
        description="最大迭代次数"
    )
    workspace: str = Field(
        default="./workspace",
        description="Agent工作区目录"
    )
    max_parallel_tools: int = Field(
        default=4,
        gt=0,
        description="并行工具执行上限"
    )


class ShellToolConfig(BaseModel):
    """Shell工具配置"""
    policy: str = Field(
        default="whitelist",
        description="安全策略（allow_all/deny_all/whitelist）"
    )
    whitelist: List[str] = Field(
        default=["echo", "ls", "dir", "cat", "type", "pwd", "cd", "head", "tail", "grep", "find", "where", "which", "python", "pip", "node", "npm", "git"],
        description="白名单命令前缀"
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="执行超时（秒）"
    )


class FileToolConfig(BaseModel):
    """文件工具配置"""
    allowed_directories: List[str] = Field(
        default=["./workspace", "./outputs"],
        description="允许访问的目录"
    )


class CodeExecutorConfig(BaseModel):
    """代码执行工具配置"""
    timeout: int = Field(
        default=30,
        gt=0,
        description="执行超时（秒）"
    )


class SearchToolConfig(BaseModel):
    """搜索工具配置"""
    enabled: bool = Field(default=False, description="是否启用")
    api_key: str = Field(default="", description="搜索API密钥")
    engine: str = Field(default="google", description="搜索引擎")


class ToolsConfig(BaseModel):
    """工具配置"""
    shell_tool: ShellToolConfig = Field(default_factory=ShellToolConfig)
    file_tool: FileToolConfig = Field(default_factory=FileToolConfig)
    code_executor: CodeExecutorConfig = Field(default_factory=CodeExecutorConfig)
    search_tool: SearchToolConfig = Field(default_factory=SearchToolConfig)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    file_path: str = Field(
        default="outputs/logs/agent.log",
        description="日志文件路径"
    )
    console_output: bool = Field(
        default=True,
        description="是否输出到控制台"
    )


class MemoryConfig(BaseModel):
    """内存配置"""
    max_entries: int = Field(
        default=100,
        gt=0,
        description="最大记忆条数"
    )
    max_context_tokens: Optional[int] = Field(
        default=None,
        gt=0,
        description="上下文最大token数（估算）"
    )
    system_token_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="系统上下文预算占比"
    )
    file_context_token_ratio: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="文件上下文预算占比"
    )
    history_token_ratio: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="对话历史预算占比"
    )
    file_context_chunk_size: int = Field(
        default=800,
        gt=0,
        description="文件分块大小（字符数）"
    )
    file_context_max_chunks_per_file: int = Field(
        default=2,
        gt=0,
        description="每个文件最大分块数"
    )
    file_context_min_score: int = Field(
        default=1,
        ge=0,
        description="分块最小相关性分数"
    )
    file_context_query_messages: int = Field(
        default=3,
        gt=0,
        description="用于检索的最近用户消息数"
    )
    type: str = Field(default="buffer", description="记忆类型")
    summary_keep_last_n: int = Field(
        default=20,
        gt=0,
        description="摘要模式保留的最近消息数"
    )
    summary_max_chars: int = Field(
        default=4000,
        gt=0,
        description="摘要最大字符数"
    )


class Config(BaseModel):
    """
    完整配置类

    统一管理所有配置项，支持从YAML文件加载
    """
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)


def find_project_root() -> Path:
    """
    查找项目根目录

    通过查找config.yaml或.git目录来确定项目根目录

    Returns:
        Path: 项目根目录路径
    """
    current_path = Path.cwd()
    
    # 向上查找包含配置文件的目录
    for parent in [current_path] + list(current_path.parents):
        if (parent / "config.yaml").exists():
            return parent
        if (parent / ".git").exists():
            return parent
    
    return current_path


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件

    优先级：
    1. 指定的配置文件路径
    2. config.local.yaml（本地配置）
    3. config.yaml（默认配置）

    Args:
        config_path: 配置文件路径

    Returns:
        Config: 配置对象
    """
    project_root = find_project_root()
    
    # 确定配置文件路径
    if config_path:
        config_file = Path(config_path)
    else:
        # 优先使用本地配置
        local_config = project_root / "config.local.yaml"
        default_config = project_root / "config.yaml"
        
        if local_config.exists():
            config_file = local_config
        elif default_config.exists():
            config_file = default_config
        else:
            # 返回默认配置
            return Config()
    
    # 读取配置文件
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
        return Config(**config_data)
    
    return Config()


def get_api_key_from_env() -> Optional[str]:
    """
    从环境变量获取API密钥

    支持多种环境变量名：
    - OPENAI_API_KEY
    - KIMI_API_KEY
    - MOONSHOT_API_KEY
    - API_KEY

    Returns:
        Optional[str]: API密钥
    """
    env_vars = ["OPENAI_API_KEY", "KIMI_API_KEY", "MOONSHOT_API_KEY", "API_KEY"]
    for var in env_vars:
        api_key = os.getenv(var)
        if api_key:
            return api_key
    return None


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """
    获取全局配置实例

    使用单例模式，确保配置只加载一次

    Returns:
        Config: 配置对象
    """
    global _config
    if _config is None:
        _config = load_config()
        
        # 如果配置文件中没有接口密钥，尝试从环境变量获取
        if not _config.model.api_key or _config.model.api_key == "your-api-key-here":
            env_api_key = get_api_key_from_env()
            if env_api_key:
                _config.model.api_key = env_api_key
    
    return _config
