# ==============================================================================
# 配置管理模块
# ==============================================================================
# 负责加载和管理项目配置
# ==============================================================================

import os
from pathlib import Path
from typing import List, Optional, Dict, Any

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
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    system_prompt_path: Optional[str] = Field(default=None, description="系统提示词文件路径")
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
    allowed_tools: List[str] = Field(default_factory=list, description="允许使用的工具名称列表")
    blocked_tools: List[str] = Field(default_factory=list, description="禁止使用的工具名称列表")
    allowed_permissions: List[str] = Field(default_factory=list, description="允许的工具权限列表")


class WorkflowConfig(BaseModel):
    """工作流可视化配置"""
    enabled: bool = Field(default=True, description="是否启用工作流可视化")
    output_dir: str = Field(default="outputs/workflows", description="输出目录")
    include_html: bool = Field(default=True, description="是否生成HTML预览")


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
    history_retrieval_enabled: bool = Field(default=True, description="是否启用历史检索")
    history_retrieval_token_ratio: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="历史检索预算占比"
    )
    history_retrieval_max_messages: int = Field(
        default=12,
        gt=0,
        description="历史检索最大消息数"
    )
    history_retrieval_min_score: int = Field(
        default=1,
        ge=0,
        description="历史检索最小分数"
    )
    history_retrieval_query_messages: int = Field(
        default=4,
        gt=0,
        description="历史检索查询消息数"
    )
    history_retrieval_include_roles: List[str] = Field(
        default_factory=lambda: ["user", "assistant"],
        description="历史检索包含角色"
    )
    project_notes_enabled: bool = Field(default=True, description="是否启用项目记忆")
    project_notes_max: int = Field(default=12, gt=0, description="项目记忆条数")
    long_term_enabled: bool = Field(default=True, description="是否启用长期记忆")
    long_term_max: int = Field(default=20, gt=0, description="长期记忆条数")
    notes_max_tokens: int = Field(default=1200, gt=0, description="记忆片段最大token预算")
    auto_note_interval: int = Field(default=18, ge=0, description="自动摘要触发间隔（消息数）")
    auto_note_min_messages: int = Field(default=6, gt=0, description="自动摘要最少消息数")
    auto_note_max_messages: int = Field(default=12, gt=0, description="自动摘要最多消息数")
    auto_note_max_chars: int = Field(default=1200, gt=0, description="自动摘要最大字符数")
    pins_enabled: bool = Field(default=True, description="是否启用置顶")
    pins_max: int = Field(default=8, gt=0, description="置顶条数上限")
    search_max_results: int = Field(default=12, gt=0, description="检索最大结果数")
    dedup_enabled: bool = Field(default=True, description="是否开启消息去重")
    dedup_window: int = Field(default=30, gt=0, description="去重窗口大小")
    auto_tag_enabled: bool = Field(default=True, description="是否开启自动标签")
    auto_tag_max: int = Field(default=6, gt=0, description="自动标签数量")
    snapshot_enabled: bool = Field(default=True, description="是否开启记忆快照")
    snapshot_max: int = Field(default=12, gt=0, description="快照保留数量")
    archive_on_reset: bool = Field(default=True, description="重置时是否归档记忆")
    archive_dir: str = Field(default="outputs/memory_archives", description="记忆归档目录")


class PluginsConfig(BaseModel):
    """插件配置"""
    enabled: bool = Field(default=False, description="是否启用插件加载")
    tool_paths: List[str] = Field(
        default_factory=lambda: ["./plugins"],
        description="插件工具搜索路径"
    )
    auto_reload: bool = Field(default=False, description="是否自动重载插件")
    catalog_files: List[str] = Field(
        default_factory=lambda: ["./plugins/catalog.json"],
        description="插件目录索引文件"
    )
    allow_unsigned: bool = Field(default=True, description="是否允许未签名插件")
    allowed_permissions: List[str] = Field(default_factory=list, description="插件权限白名单")


class ArtifactsConfig(BaseModel):
    """产物配置"""
    output_dir: str = Field(default="outputs", description="产物输出目录")
    save_context_snapshot: bool = Field(default=True, description="是否保存上下文快照")
    context_snapshot_max_messages: int = Field(
        default=50,
        gt=0,
        description="快照保留的消息数"
    )
    context_snapshot_include_files: bool = Field(default=True, description="快照是否包含文件")
    context_snapshot_include_messages: bool = Field(default=True, description="快照是否包含对话消息")
    context_snapshot_include_summary: bool = Field(default=True, description="快照是否包含摘要")
    save_tool_metrics: bool = Field(default=True, description="是否保存工具指标")
    archive_dir: str = Field(default="outputs/archives", description="归档目录")
    cleanup_enabled: bool = Field(default=False, description="是否启用自动清理")
    cleanup_keep_recent: int = Field(default=50, gt=0, description="保留最近任务数量")
    cleanup_max_days: Optional[int] = Field(default=None, gt=0, description="清理最大保留天数")
    cleanup_keep_failed: bool = Field(default=True, description="清理时是否保留失败任务")


class ObservabilityConfig(BaseModel):
    """可观测性配置"""
    enabled: bool = Field(default=True, description="是否启用工具指标统计")
    metrics_file: str = Field(default="outputs/tool_metrics.json", description="指标文件路径")
    metrics_csv_file: str = Field(default="outputs/tool_metrics.csv", description="指标CSV路径")
    export_csv: bool = Field(default=True, description="是否导出CSV")


class ProfileConfig(BaseModel):
    """角色模板配置"""
    name: str = Field(default="default", description="模板名称")
    description: str = Field(default="", description="模板说明")
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    system_prompt_path: Optional[str] = Field(default=None, description="系统提示词文件路径")
    append_tools_description: bool = Field(default=True, description="是否附加工具描述")
    tools_include: List[str] = Field(default_factory=list, description="包含的工具名称")
    tools_exclude: List[str] = Field(default_factory=list, description="排除的工具名称")
    config_overrides: Dict[str, Any] = Field(default_factory=dict, description="配置覆盖项")


class QueueConfig(BaseModel):
    """任务队列配置"""
    enabled: bool = Field(default=True, description="是否启用任务队列")
    queue_file: str = Field(default="outputs/task_queue.json", description="队列文件路径")
    max_retries: int = Field(default=1, ge=0, description="失败最大重试次数")
    auto_resume: bool = Field(default=True, description="启动时自动恢复未完成任务")


class SchedulerConfig(BaseModel):
    """调度配置"""
    enabled: bool = Field(default=True, description="是否启用调度")
    schedule_file: str = Field(default="outputs/schedule.json", description="调度任务文件")
    poll_interval: float = Field(default=2.0, gt=0, description="调度轮询间隔（秒）")
    max_pending: int = Field(default=200, gt=0, description="最大待执行任务数")
    rollback_on_failure: bool = Field(default=True, description="失败时是否回滚会话")
    triggers: List[Dict[str, Any]] = Field(default_factory=list, description="触发器配置列表")


class DashboardConfig(BaseModel):
    """仪表盘配置"""
    enabled: bool = Field(default=True, description="是否启用任务仪表盘")
    host: str = Field(default="127.0.0.1", description="监听地址")
    port: int = Field(default=8765, description="监听端口")
    title: str = Field(default="SAMA Dashboard", description="页面标题")
    auto_open: bool = Field(default=False, description="是否自动打开浏览器")


class ChatUIConfig(BaseModel):
    """聊天前端配置"""
    enabled: bool = Field(default=True, description="是否启用聊天前端")
    host: str = Field(default="127.0.0.1", description="监听地址")
    port: int = Field(default=8790, description="监听端口")
    title: str = Field(default="sama", description="页面标题")
    auto_open: bool = Field(default=False, description="是否自动打开浏览器")
    max_port_tries: int = Field(default=10, ge=1, description="端口占用时的最大尝试次数")
    max_body_size: int = Field(default=20000, gt=0, description="请求体最大字节数")
    profile: Optional[str] = Field(default=None, description="默认模板名称")
    allow_config_update: bool = Field(default=True, description="是否允许通过WebUI更新配置")
    collaboration_enabled: bool = Field(default=True, description="是否启用协作会话")
    collaboration_timeout: int = Field(default=300, gt=0, description="协作客户端超时秒数")
    session_store_enabled: bool = Field(default=True, description="是否启用会话存储")
    session_store_dir: str = Field(default="outputs/sessions", description="会话存储目录")


class AuditConfig(BaseModel):
    """审计配置"""
    enabled: bool = Field(default=True, description="是否启用审计日志")
    file_path: str = Field(default="outputs/audit.log", description="审计日志路径")
    redact_enabled: bool = Field(default=True, description="是否进行敏感信息脱敏")


class NotificationEventConfig(BaseModel):
    """通知事件配置"""
    enabled: bool = Field(default=False, description="是否启用")
    message: str = Field(default="", description="消息模板")
    webhook_url: Optional[str] = Field(default=None, description="Webhook地址")
    webhook_headers: Dict[str, str] = Field(default_factory=dict, description="Webhook请求头")
    webhook_timeout: int = Field(default=5, gt=0, description="Webhook超时秒数")
    command: Optional[str] = Field(default=None, description="回调命令")
    write_file: Optional[str] = Field(default=None, description="写入文件路径")
    sound: bool = Field(default=False, description="是否播放提示音")


class NotificationsConfig(BaseModel):
    """通知配置"""
    enabled: bool = Field(default=False, description="是否启用通知")
    on_success: NotificationEventConfig = Field(default_factory=NotificationEventConfig)
    on_failure: NotificationEventConfig = Field(default_factory=NotificationEventConfig)
    on_queue_complete: NotificationEventConfig = Field(default_factory=NotificationEventConfig)


class KnowledgeBaseConfig(BaseModel):
    """本地知识库配置"""
    enabled: bool = Field(default=True, description="是否启用知识库")
    index_file: str = Field(default="outputs/knowledge_index.jsonl", description="索引文件路径")
    meta_file: str = Field(default="outputs/knowledge_meta.json", description="索引元数据路径")
    chunk_size: int = Field(default=1200, gt=0, description="分块大小（字符）")
    max_chunks_per_file: int = Field(default=6, gt=0, description="每个文件最大分块数")
    max_file_size: Optional[int] = Field(default=2000000, gt=0, description="最大文件大小（字节）")
    skip_binary: bool = Field(default=True, description="是否跳过二进制文件")
    include_extensions: List[str] = Field(
        default_factory=lambda: [".md", ".txt", ".py", ".json", ".yaml", ".yml"],
        description="包含的文件扩展名"
    )
    exclude_dirs: List[str] = Field(
        default_factory=lambda: ["outputs", "workspace", ".git", "__pycache__"],
        description="排除目录"
    )
    min_score: int = Field(default=1, ge=0, description="最小匹配分数")
    max_results: int = Field(default=6, gt=0, description="最大结果数")
    snippet_length: int = Field(default=240, gt=0, description="摘要长度")


class NewsDigestConfig(BaseModel):
    """新闻摘要配置"""
    enabled: bool = Field(default=False, description="是否启用新闻摘要")
    schedule_time: str = Field(default="12:00", description="每日推送时间（HH:MM）")
    topics: List[str] = Field(default_factory=lambda: ["AI", "科技", "投资"], description="关注主题关键词")
    output_dir: str = Field(default="outputs/news", description="输出目录")
    obsidian_enabled: bool = Field(default=False, description="是否推送到Obsidian")
    obsidian_dir: str = Field(default="", description="Obsidian目标目录")
    obsidian_filename: str = Field(default="news_{date}.md", description="Obsidian文件名模板")
    max_items: int = Field(default=40, gt=0, description="最大条目数")
    per_topic_limit: int = Field(default=6, gt=0, description="每个主题条目数上限")
    sources: List[str] = Field(
        default_factory=lambda: [
            "https://news.google.com/rss/search?q={topic}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        ],
        description="RSS来源列表（支持 {topic} 占位）"
    )


class MediaHubConfig(BaseModel):
    """媒体中心配置"""
    enabled: bool = Field(default=True, description="是否启用媒体中心")
    schedule_time: str = Field(default="12:00", description="每日抓取时间（HH:MM）")
    output_dir: str = Field(default="outputs/media", description="输出目录")
    sources_file: str = Field(default="outputs/media/sources.json", description="订阅源文件")
    items_file: str = Field(default="outputs/media/items.json", description="条目存储文件")
    alerts_file: str = Field(default="outputs/media/alerts.json", description="告警文件")
    brief_dir: str = Field(default="outputs/media/briefs", description="日报目录")
    obsidian_enabled: bool = Field(default=False, description="是否推送到Obsidian")
    obsidian_dir: str = Field(default="", description="Obsidian目标目录")
    obsidian_filename: str = Field(default="media_{date}.md", description="Obsidian文件名模板")
    max_items: int = Field(default=2000, gt=0, description="最大条目数")
    per_source_limit: int = Field(default=80, gt=0, description="每个源抓取上限")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="订阅源配置列表")
    alerts: List[str] = Field(default_factory=list, description="告警关键词")


class Config(BaseModel):
    """
    完整配置类

    统一管理所有配置项，支持从YAML文件加载
    """
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    artifacts: ArtifactsConfig = Field(default_factory=ArtifactsConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    profiles: List[ProfileConfig] = Field(default_factory=list)
    active_profile: Optional[str] = Field(default=None, description="默认启用的模板")
    queue: QueueConfig = Field(default_factory=QueueConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    chat_ui: ChatUIConfig = Field(default_factory=ChatUIConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    knowledge_base: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    news_digest: NewsDigestConfig = Field(default_factory=NewsDigestConfig)
    media_hub: MediaHubConfig = Field(default_factory=MediaHubConfig)


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
    2. config.yaml（默认配置）
    3. config.local.yaml（本地覆盖）
    4. config.d/*.yaml（额外覆盖）
    5. 环境变量 SAMA_CONFIG_OVERLAYS 指定的覆盖文件

    Args:
        config_path: 配置文件路径

    Returns:
        Config: 配置对象
    """
    project_root = find_project_root()
    
    config_files: List[Path] = []

    if config_path:
        config_files.append(Path(config_path))
    else:
        default_config = project_root / "config.yaml"
        local_config = project_root / "config.local.yaml"
        if default_config.exists():
            config_files.append(default_config)
        if local_config.exists():
            config_files.append(local_config)
        overlay_dir = project_root / "config.d"
        if overlay_dir.exists():
            config_files.extend(sorted(overlay_dir.glob("*.yaml")))

    overlay_env = os.getenv("SAMA_CONFIG_OVERLAYS")
    if overlay_env:
        for raw in overlay_env.split(os.pathsep):
            raw = raw.strip()
            if raw:
                config_files.append(Path(raw))

    config_data: Dict[str, Any] = {}
    for path in config_files:
        if not path.exists():
            continue
        config_data = _deep_merge_dict(config_data, _read_yaml(path))

    if not config_data:
        return Config()

    profile_defs = _load_profiles_from_dir(project_root / "profiles")
    if profile_defs:
        config_data.setdefault("profiles", [])
        if isinstance(config_data["profiles"], list):
            config_data["profiles"].extend(profile_defs)

    active_profile = os.getenv("SAMA_PROFILE") or config_data.get("active_profile")
    if active_profile:
        profile_data = _find_profile_data(config_data.get("profiles"), active_profile)
        if profile_data:
            overrides = profile_data.get("config_overrides") or {}
            if isinstance(overrides, dict) and overrides:
                config_data = _deep_merge_dict(config_data, overrides)
            config_data["active_profile"] = active_profile

    return Config(**config_data)


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


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典，覆盖项优先生效
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_profiles_from_dir(path: Path) -> List[Dict[str, Any]]:
    if not path.exists() or not path.is_dir():
        return []
    profiles: List[Dict[str, Any]] = []
    for file_path in sorted(path.glob("*.yaml")):
        data = _read_yaml(file_path)
        if not data:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    profiles.append(_ensure_profile_name(item, file_path))
            continue
        if isinstance(data, dict):
            if "profiles" in data and isinstance(data["profiles"], list):
                for item in data["profiles"]:
                    if isinstance(item, dict):
                        profiles.append(_ensure_profile_name(item, file_path))
            else:
                profiles.append(_ensure_profile_name(data, file_path))
    return profiles


def _ensure_profile_name(data: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
    if not data.get("name"):
        data = dict(data)
        data["name"] = file_path.stem
    return data


def _find_profile_data(profiles: Any, name: str) -> Optional[Dict[str, Any]]:
    if not profiles or not isinstance(profiles, list):
        return None
    for profile in profiles:
        if isinstance(profile, dict) and profile.get("name") == name:
            return profile
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
