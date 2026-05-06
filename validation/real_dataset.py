"""Real-world test dataset extracted from Hermes session history.

Source: Actual conversations between Boss and HNOE about Mnemonic project.
"""

# ─── 真实对话数据集（从session历史提取）──────────────────────────────────

REAL_CONVERSATIONS = [
    # Session: 20260502_085021_ad685fce - Vector搜索修复
    {
        "id": "real_001",
        "session_id": "20260502_085021_ad685fce",
        "messages": [
            {"role": "user", "content": "昨天你说插件是怎么加载的？"},
            {"role": "assistant", "content": "Hermes PluginManager 自动扫描 4 个来源：Bundled、User、Project、pip entry_points。插件自动发现但不自动启用，需显式配置。"},
        ],
        "expected_memories": [
            {"content": "Hermes PluginManager 自动扫描 4 个来源：Bundled、User、Project、pip entry_points", "type": "fact", "importance": 0.8},
            {"content": "Hermes 插件自动发现但不自动启用，需显式配置", "type": "fact", "importance": 0.8},
        ],
        "category": "technical",
    },
    {
        "id": "real_002",
        "session_id": "20260502_085021_ad685fce",
        "messages": [
            {"role": "user", "content": "Vector搜索L1只有13.3%，怎么修复？"},
            {"role": "assistant", "content": "发现 SiliconFlow Embedding API Key 无效，EmbeddingService 自动 fallback 到 _pseudo_embed()（哈希伪向量）。需要更新 .env 文件中的 MNEMONIC_EMBEDDING_API_KEY。"},
        ],
        "expected_memories": [
            {"content": "Vector搜索L1从13.3%提升到53.3%的原因是API Key无效导致fallback到伪向量", "type": "fact", "importance": 0.9},
            {"content": "Mnemonic EmbeddingService在API Key无效时会fallback到_pseudo_embed()伪向量", "type": "fact", "importance": 0.8},
        ],
        "category": "debugging",
    },
    {
        "id": "real_003",
        "session_id": "20260502_085021_ad685fce",
        "messages": [
            {"role": "user", "content": "修复后Vector搜索效果如何？"},
            {"role": "assistant", "content": "Vector L1从13.3%提升到53.3%，L3从0.22提升到0.62。Keyword L1=60%，L3=0.63。Hybrid L1从46.7%提升到60%。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic Vector搜索修复后：L1=53.3%, L3=0.62；Keyword L1=60%, L3=0.63；Hybrid L1=60%, L3=0.67", "type": "fact", "importance": 0.8},
        ],
        "category": "metrics",
    },
    
    # Session: 20260501_074950_fb43dd61 - 四维测试结果
    {
        "id": "real_004",
        "session_id": "20260501_074950_fb43dd61",
        "messages": [
            {"role": "user", "content": "Mnemonic四维测试结果怎么样？"},
            {"role": "assistant", "content": "D1 Extraction F1=0.974，D2 Recency 100%，D3 Robustness 0%，D4 Keyword L1=80%, MRR=0.85。Keyword搜索优于Vector搜索，原因是BGE-M3中文embedding质量问题。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic四维测试v5结果：D1 F1=0.974, D2 100%, D3 0%, D4 Keyword L1=80% MRR=0.85", "type": "fact", "importance": 0.9},
            {"content": "Keyword搜索优于Vector搜索的原因是BGE-M3中文embedding质量问题", "type": "fact", "importance": 0.7},
        ],
        "category": "metrics",
    },
    {
        "id": "real_005",
        "session_id": "20260501_074950_fb43dd61",
        "messages": [
            {"role": "user", "content": "Mnemonic架构设计有什么特点？"},
            {"role": "assistant", "content": "三组件架构：Mnemonic Server + Mnemonic SDK + Mnemonic Hermes Plugin。存储使用PostgreSQL + pgvector。与mem0的差异化：遗忘机制（TTL、importance decay、access frequency weighting）。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic三组件架构：Server + SDK + Hermes Plugin", "type": "fact", "importance": 0.8},
            {"content": "Mnemonic存储使用PostgreSQL + pgvector", "type": "fact", "importance": 0.7},
            {"content": "Mnemonic与mem0的差异化：遗忘机制（TTL、importance decay、access frequency weighting）", "type": "fact", "importance": 0.9},
        ],
        "category": "architecture",
    },
    
    # Session: 20260505_150731_77ecd6e2 - 数据丢失与恢复
    {
        "id": "real_006",
        "session_id": "20260505_150731_77ecd6e2",
        "messages": [
            {"role": "user", "content": "为什么postgres没有任何数据了？"},
            {"role": "assistant", "content": "数据库可能被重建/重置了。之前有17条记录，现在只剩2条测试数据。表结构也是新的，有个entities表之前不存在。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic PostgreSQL数据库在192.168.0.101:8771曾丢失数据，从17条降到2条", "type": "event", "importance": 0.7},
        ],
        "category": "incident",
    },
    {
        "id": "real_007",
        "session_id": "20260505_150731_77ecd6e2",
        "messages": [
            {"role": "user", "content": "怎么恢复数据？"},
            {"role": "assistant", "content": "从MEMORY block导入14条核心记忆。需要添加x-namespace header。API endpoint是http://localhost:8010。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic API需要x-namespace header", "type": "fact", "importance": 0.8},
            {"content": "Mnemonic API endpoint是http://localhost:8010", "type": "fact", "importance": 0.7},
        ],
        "category": "operation",
    },
    
    # Session: 20260429_113027_eb47377a - 架构设计
    {
        "id": "real_008",
        "session_id": "20260429_113027_eb47377a",
        "messages": [
            {"role": "user", "content": "mem0有什么优势和劣势？"},
            {"role": "assistant", "content": "优势：四操作语义（ADD/UPDATE/DELETE/NOOP）生产验证；User/Session/Agent三级隔离；REST API完善。劣势：每次写入3次LLM调用成本高；无遗忘机制；Neo4j强依赖；Context Bloat问题。"},
        ],
        "expected_memories": [
            {"content": "mem0优势：四操作语义生产验证、三级隔离、REST API完善", "type": "fact", "importance": 0.8},
            {"content": "mem0劣势：3次LLM调用成本高、无遗忘机制、Neo4j强依赖、Context Bloat", "type": "fact", "importance": 0.8},
        ],
        "category": "analysis",
    },
    {
        "id": "real_009",
        "session_id": "20260429_113027_eb47377a",
        "messages": [
            {"role": "user", "content": "Hermes MemoryProvider需要实现哪些方法？"},
            {"role": "assistant", "content": "ABC必须实现：name、is_available()、initialize(session_id, kwargs)、get_tool_schemas()、handle_tool_call(name, args)、get_config_schema()、save_config(values, hermes_home)。可选Hooks：prefetch()、sync_turn()、on_session_end()、on_pre_compress()、shutdown()。"},
        ],
        "expected_memories": [
            {"content": "Hermes MemoryProvider ABC必须实现7个方法：name、is_available、initialize、get_tool_schemas、handle_tool_call、get_config_schema、save_config", "type": "fact", "importance": 0.9},
            {"content": "Hermes MemoryProvider可选Hooks：prefetch、sync_turn、on_session_end、on_pre_compress、shutdown", "type": "fact", "importance": 0.7},
        ],
        "category": "technical",
    },
    {
        "id": "real_010",
        "session_id": "20260429_113027_eb47377a",
        "messages": [
            {"role": "user", "content": "Mnemonic定义了哪几种记忆类型？"},
            {"role": "assistant", "content": "6种记忆类型：Preference（偏好）、Fact（事实）、Event（事件）、Context（上下文）、Pattern（模式）、Skill（技能）。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic定义6种记忆类型：Preference、Fact、Event、Context、Pattern、Skill", "type": "fact", "importance": 0.8},
        ],
        "category": "design",
    },
    
    # Session: 20260503_221325_fa806aec - 文档补充
    {
        "id": "real_011",
        "session_id": "20260503_221325_fa806aec",
        "messages": [
            {"role": "user", "content": "README.md缺了如何hermes如何安装mnemonic"},
            {"role": "assistant", "content": "已添加Hermes Agent集成章节，包括前置条件、配置步骤、验证方法、Fallback机制说明。插件位置：/Users/kopa/.hermes/hermes-agent/plugins/memory/mnemonic/。配置文件：$HERMES_HOME/mnemonic.json。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic Hermes插件位置：/Users/kopa/.hermes/hermes-agent/plugins/memory/mnemonic/", "type": "fact", "importance": 0.7},
            {"content": "Mnemonic配置文件路径：$HERMES_HOME/mnemonic.json", "type": "fact", "importance": 0.7},
        ],
        "category": "documentation",
    },
    
    # 冲突场景（基于真实数据）
    {
        "id": "real_conflict_001",
        "session_id": "synthetic",
        "messages": [
            {"role": "user", "content": "Vector搜索L1是多少？"},
            {"role": "assistant", "content": "之前是13.3%，修复后是53.3%。"},
        ],
        "expected_memories": [
            {"content": "Vector搜索L1是53.3%", "type": "fact", "importance": 0.8},
        ],
        "conflict_with": "real_002",  # 之前说13.3%
        "category": "conflict",
    },
    {
        "id": "real_conflict_002",
        "session_id": "synthetic",
        "messages": [
            {"role": "user", "content": "数据库现在有多少条记忆？"},
            {"role": "assistant", "content": "16条记录。"},
        ],
        "expected_memories": [
            {"content": "Mnemonic数据库有16条记忆", "type": "fact", "importance": 0.6},
        ],
        "conflict_with": "real_006",  # 之前说2条
        "category": "conflict",
    },
    
    # 噪声对话（真实无意义对话）
    {
        "id": "real_noise_001",
        "session_id": "synthetic",
        "messages": [
            {"role": "user", "content": "好的"},
            {"role": "assistant", "content": "收到，还有其他问题吗？"},
        ],
        "expected_memories": [],  # 不应提取记忆
        "category": "noise",
    },
    {
        "id": "real_noise_002",
        "session_id": "synthetic",
        "messages": [
            {"role": "user", "content": "谢谢"},
            {"role": "assistant", "content": "不客气！"},
        ],
        "expected_memories": [],  # 不应提取记忆
        "category": "noise",
    },
]

# ─── 真实搜索查询（基于实际使用场景）──────────────────────────────────

REAL_SEARCH_QUERIES = [
    {
        "id": "real_query_001",
        "query": "Hermes插件怎么加载的？",
        "expected_memory_ids": ["real_001"],
        "expected_content_keywords": ["PluginManager", "扫描", "4个来源"],
    },
    {
        "id": "real_query_002",
        "query": "Vector搜索为什么效果差？",
        "expected_memory_ids": ["real_002", "real_004"],
        "expected_content_keywords": ["API Key", "fallback", "伪向量", "BGE-M3"],
    },
    {
        "id": "real_query_003",
        "query": "Mnemonic四维测试结果",
        "expected_memory_ids": ["real_004"],
        "expected_content_keywords": ["D1", "F1", "0.974", "L1", "80%"],
    },
    {
        "id": "real_query_004",
        "query": "mem0有什么问题？",
        "expected_memory_ids": ["real_008"],
        "expected_content_keywords": ["劣势", "LLM调用", "遗忘机制", "Neo4j"],
    },
    {
        "id": "real_query_005",
        "query": "MemoryProvider需要实现什么？",
        "expected_memory_ids": ["real_009"],
        "expected_content_keywords": ["ABC", "7个方法", "initialize", "handle_tool_call"],
    },
    {
        "id": "real_query_006",
        "query": "Mnemonic架构设计",
        "expected_memory_ids": ["real_005", "real_010"],
        "expected_content_keywords": ["三组件", "Server", "SDK", "Plugin", "6种记忆类型"],
    },
    {
        "id": "real_query_007",
        "query": "数据库连接信息",
        "expected_memory_ids": ["real_006", "real_007"],
        "expected_content_keywords": ["192.168.0.101:8771", "PostgreSQL", "localhost:8010"],
    },
    {
        "id": "real_query_008",
        "query": "Mnemonic和mem0的区别",
        "expected_memory_ids": ["real_005", "real_008"],
        "expected_content_keywords": ["遗忘机制", "TTL", "importance decay", "差异化"],
    },
]

# ─── 统计信息 ──────────────────────────────────────────────────────

DATASET_STATS = {
    "total_conversations": len(REAL_CONVERSATIONS),
    "by_category": {
        "technical": 3,
        "debugging": 1,
        "metrics": 2,
        "architecture": 1,
        "incident": 1,
        "operation": 1,
        "analysis": 1,
        "design": 1,
        "documentation": 1,
        "conflict": 2,
        "noise": 2,
    },
    "total_expected_memories": sum(len(c["expected_memories"]) for c in REAL_CONVERSATIONS),
    "total_search_queries": len(REAL_SEARCH_QUERIES),
    "source_sessions": [
        "20260502_085021_ad685fce",
        "20260501_074950_fb43dd61",
        "20260505_150731_77ecd6e2",
        "20260429_113027_eb47377a",
        "20260503_221325_fa806aec",
    ],
}