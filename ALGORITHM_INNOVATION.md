# Mnemonic算法创新设计方案

基于mem0论文和IGMiRAG论文的深度分析，提出以下算法创新：

---

## 一、mem0核心算法分析

### 1. 记忆提取与更新（Algorithm 1）

**现有流程**：
```
1. LLM提取事实 ωi ∈ Ω
2. 向量检索top-s相似记忆
3. LLM决策操作：ADD/UPDATE/DELETE/NOOP
4. 执行操作
```

**关键参数**：
- m = 10（上下文窗口）
- s = 10（相似记忆数量）

**问题**：
- 固定参数，无法适应不同场景
- 无时间衰减机制
- 无重要性动态调整

---

### 2. Mem0g图记忆架构

**核心设计**：
```
G = (V, E, L)
- V: 实体节点（Person, Location, Event）
- E: 关系边（lives_in, prefers, owns）
- L: 标签（语义类型）

实体节点v包含：
1. entity_type（类型）
2. embedding vector ev（语义向量）
3. metadata + timestamp tv（时间戳）
```

**创新点**：
- 图结构捕获复杂关系
- 双检索策略：entity-centric + semantic triplet
- 冲突检测机制

---

## 二、IGMiRAG核心算法分析

### 1. 层次化异构超图

**核心设计**：
```
Hierarchical Heterogeneous Hypergraph
- 多粒度知识对齐
- 推理路径模拟记忆结构
- 双焦点检索（dual-focus retrieval）
```

**关键创新**：
1. **直觉引导**：问题解析器控制挖掘深度
2. **双向扩散算法**：沿推理路径挖掘深度记忆
3. **自适应成本**：token成本随任务复杂度调整（3k-6k+）

---

## 三、Mnemonic算法创新方案

### 创新1：时间衰减记忆重要性（Temporal Decay Importance）

**理论基础**：人类记忆随时间衰减（Ebbinghaus遗忘曲线）

**算法设计**：
```python
class TemporalDecayImportance:
    """时间衰减重要性算法"""

    def calculate_importance(self, memory, current_time):
        """
        基于Ebbinghaus遗忘曲线的记忆重要性计算

        I(t) = I_0 * e^(-λt) * access_boost

        参数：
        - I_0: 初始重要性（LLM提取时设定）
        - λ: 衰减率（可配置）
        - t: 时间间隔（天）
        - access_boost: 访问次数加成
        """
        days_elapsed = (current_time - memory.created_at).days

        # Ebbinghaus曲线：R = e^(-t/S)，S=记忆强度
        decay_factor = math.exp(-self.decay_rate * days_elapsed)

        # 访问次数加成（每次访问提升重要性）
        access_boost = 1 + 0.1 * memory.access_count

        # 最终重要性
        importance = memory.initial_importance * decay_factor * access_boost

        # 最低阈值（防止完全遗忘）
        return max(importance, self.min_threshold)

    def update_decay_rate(self, memory_type):
        """
        不同类型记忆使用不同衰减率

        - 事实（fact）：慢衰减（λ=0.05）
        - 偏好（preference）：中衰减（λ=0.1）
        - 事件（event）：快衰减（λ=0.2）
        """
        rates = {
            'fact': 0.05,      # 长期记忆
            'preference': 0.1, # 中期记忆
            'event': 0.2,      # 短期记忆
            'procedure': 0.03  # 技能记忆（最稳定）
        }
        return rates.get(memory_type, 0.1)
```

**实现路径**：
1. 在Memory模型添加字段：
   - `initial_importance`（初始重要性）
   - `access_count`（访问次数）
   - `last_accessed_at`（最后访问时间）

2. 在检索时动态计算重要性：
   ```sql
   SELECT *,
          initial_importance * exp(-decay_rate * days_elapsed) * (1 + 0.1 * access_count) as dynamic_importance
   FROM memories
   ORDER BY dynamic_importance DESC, similarity DESC
   ```

---

### 创新2：自适应记忆提取窗口（Adaptive Extraction Window）

**理论基础**：IGMiRAG的自适应成本控制

**算法设计**：
```python
class AdaptiveExtractionWindow:
    """自适应记忆提取窗口"""

    def determine_window_size(self, conversation_context):
        """
        根据对话复杂度动态调整提取窗口

        参数：
        - conversation_context: 对话上下文分析结果

        返回：
        - m: 上下文窗口大小（5-20）
        - s: 相似记忆检索数量（5-15）
        """
        # 分析对话复杂度
        complexity = self._analyze_complexity(conversation_context)

        # 低复杂度：小窗口（快速）
        if complexity < 0.3:
            return {'m': 5, 's': 5, 'mode': 'fast'}

        # 中复杂度：标准窗口
        elif complexity < 0.7:
            return {'m': 10, 's': 10, 'mode': 'standard'}

        # 高复杂度：大窗口（深度）
        else:
            return {'m': 20, 's': 15, 'mode': 'deep'}

    def _analyze_complexity(self, context):
        """
        分析对话复杂度指标：
        1. 实体数量（entities count）
        2. 关系密度（relation density）
        3. 时间跨度（temporal span）
        4. 话题切换次数（topic switches）
        """
        # 实体数量
        entity_count = len(extract_entities(context))

        # 关系密度（实体间连接数/实体数）
        relation_density = self._calculate_relation_density(context)

        # 时间跨度（对话跨越的天数）
        temporal_span = self._calculate_temporal_span(context)

        # 话题切换次数
        topic_switches = self._detect_topic_switches(context)

        # 综合复杂度评分
        complexity = (
            0.3 * min(entity_count / 10, 1.0) +
            0.3 * relation_density +
            0.2 * min(temporal_span / 7, 1.0) +
            0.2 * min(topic_switches / 5, 1.0)
        )

        return complexity
```

**实现路径**：
1. 在提取前分析对话复杂度
2. 动态调整LLM调用参数
3. 记录复杂度指标用于后续优化

---

### 创新3：双向扩散记忆检索（Bidirectional Diffusion Retrieval）

**理论基础**：IGMiRAG的双向扩散算法

**算法设计**：
```python
class BidirectionalDiffusionRetrieval:
    """双向扩散记忆检索"""

    def retrieve(self, query, knowledge_graph):
        """
        从查询实体出发，双向扩散检索关联记忆

        步骤：
        1. 提取查询实体
        2. 前向扩散：沿出边探索（因果关系）
        3. 后向扩散：沿入边探索（溯源关系）
        4. 合并结果，按路径长度排序
        """
        # 提取查询实体
        query_entities = self._extract_query_entities(query)

        # 前向扩散（因果关系）
        forward_memories = self._forward_diffusion(
            query_entities,
            max_depth=3,
            time_window=7  # 7天内
        )

        # 后向扩散（溯源关系）
        backward_memories = self._backward_diffusion(
            query_entities,
            max_depth=2,
            time_window=30  # 30天内
        )

        # 合并并排序
        combined = self._merge_and_rank(
            forward_memories,
            backward_memories,
            query
        )

        return combined

    def _forward_diffusion(self, entities, max_depth, time_window):
        """
        前向扩散：探索实体的影响

        例如：
        A -> lives_in -> San Francisco
        San Francisco -> located_in -> California

        查询"A在哪里"时：
        1. 找到A
        2. 前向扩散到San Francisco
        3. 继续扩散到California（可选）
        """
        visited = set()
        memories = []

        for entity in entities:
            self._diffuse_from_node(
                entity,
                direction='outgoing',
                depth=max_depth,
                visited=visited,
                memories=memories,
                time_window=time_window
            )

        return memories

    def _backward_diffusion(self, entities, max_depth, time_window):
        """
        后向扩散：探索实体的来源

        例如：
        A <- friends <- B
        B <- works_at <- Company X

        查询"A的朋友在哪里工作"时：
        1. 找到A
        2. 后向扩散找到B（friends关系）
        3. 继续扩散找到Company X
        """
        visited = set()
        memories = []

        for entity in entities:
            self._diffuse_from_node(
                entity,
                direction='incoming',
                depth=max_depth,
                visited=visited,
                memories=memories,
                time_window=time_window
            )

        return memories
```

**实现路径**：
1. 在Entity表添加关系字段：
   - `source_entities`（来源实体）
   - `target_entities`（目标实体）
   - `relation_type`（关系类型）

2. 构建实体关系图：
   ```sql
   CREATE TABLE entity_relations (
       id UUID PRIMARY KEY,
       source_entity_id UUID,
       target_entity_id UUID,
       relation_type VARCHAR(50),
       confidence FLOAT,
       created_at TIMESTAMP
   );
   ```

3. 实现扩散检索算法

---

### 创新4：冲突检测与记忆合并（Conflict Detection & Memory Merging）

**理论基础**：Mem0g的冲突检测机制

**算法设计**：
```python
class ConflictDetectionMerging:
    """冲突检测与记忆合并"""

    def detect_conflicts(self, new_memory, existing_memories):
        """
        检测新记忆与现有记忆的冲突

        冲突类型：
        1. 直接矛盾（direct contradiction）
        2. 时间矛盾（temporal contradiction）
        3. 部分矛盾（partial contradiction）
        """
        conflicts = []

        for existing in existing_memories:
            # LLM判断冲突类型
            conflict_type = self._llm_detect_conflict(
                new_memory,
                existing
            )

            if conflict_type != 'none':
                conflicts.append({
                    'existing_memory': existing,
                    'conflict_type': conflict_type,
                    'resolution_strategy': self._get_resolution_strategy(conflict_type)
                })

        return conflicts

    def resolve_conflict(self, conflict, new_memory):
        """
        冲突解决策略：

        1. 直接矛盾：
           - 标记旧记忆为invalid
           - 创建新记忆

        2. 时间矛盾：
           - 保留两者，添加时间戳
           - 检索时按时间排序

        3. 部分矛盾：
           - 合并记忆（LLM生成合并版本）
           - 删除旧记忆，创建合并记忆
        """
        strategy = conflict['resolution_strategy']

        if strategy == 'invalidate_old':
            # 标记旧记忆无效
            self._mark_invalid(conflict['existing_memory'])
            # 创建新记忆
            return new_memory

        elif strategy == 'keep_both':
            # 保留两者，添加时间戳区分
            return self._add_temporal_context(new_memory, conflict['existing_memory'])

        elif strategy == 'merge':
            # LLM合并记忆
            merged = self._llm_merge_memories(new_memory, conflict['existing_memory'])
            # 删除旧记忆
            self._delete(conflict['existing_memory'])
            return merged

    def _llm_detect_conflict(self, new, existing):
        """
        使用LLM判断冲突类型

        Prompt:
        Given two memories:
        1. New: "{new.content}"
        2. Existing: "{existing.content}"

        Determine the conflict type:
        - direct_contradiction: They directly contradict each other
        - temporal_contradiction: They describe different time periods
        - partial_contradiction: They partially overlap but have differences
        - none: No conflict

        Return JSON: {"conflict_type": "...", "reason": "..."}
        """
        prompt = self._build_conflict_detection_prompt(new, existing)
        response = self.llm_client.chat_completion(prompt)
        return self._parse_conflict_response(response)
```

**实现路径**：
1. 在Memory表添加字段：
   - `status`（active/invalid/merged）
   - `invalidated_at`（失效时间）
   - `invalidated_by`（失效原因）

2. 在更新流程中集成冲突检测

---

### 创新5：记忆压缩与摘要（Memory Compression & Summarization）

**理论基础**：降低token成本，提高检索效率

**算法设计**：
```python
class MemoryCompression:
    """记忆压缩与摘要"""

    def compress_memories(self, memories, target_length=100):
        """
        将多条相关记忆压缩为一条摘要记忆

        适用场景：
        1. 同一实体的多条记忆（如"A喜欢..."的多条记录）
        2. 同一时间段的多条记忆
        3. 同一主题的多条记忆
        """
        # 按实体/时间/主题分组
        groups = self._group_memories(memories)

        compressed = []
        for group in groups:
            # LLM生成摘要
            summary = self._llm_summarize(group)

            # 创建摘要记忆
            compressed_memory = {
                'content': summary,
                'type': 'summary',
                'source_memories': [m.id for m in group],
                'compression_ratio': len(group) / 1
            }
            compressed.append(compressed_memory)

        return compressed

    def _llm_summarize(self, memories):
        """
        LLM摘要多条记忆

        Prompt:
        Summarize the following memories into a single concise statement:

        {memories}

        Requirements:
        - Keep all key facts
        - Remove redundancy
        - Preserve temporal information
        - Output in the same language as input
        """
        prompt = self._build_summarization_prompt(memories)
        return self.llm_client.chat_completion(prompt)
```

**实现路径**：
1. 定期执行压缩任务（如每周）
2. 压缩后的记忆标记为`summary`类型
3. 检索时优先返回摘要，展开时返回原始记忆

---

## 四、实现优先级

### Phase 1（立即实现）：时间衰减重要性
- 理论成熟（Ebbinghaus曲线）
- 实现简单（添加字段+计算公式）
- 效果明显（提高检索质量）

### Phase 2（短期）：自适应提取窗口
- 基于IGMiRAG的自适应成本控制
- 降低LLM调用成本
- 提高提取效率

### Phase 3（中期）：冲突检测与合并
- 基于Mem0g的冲突检测机制
- 提高记忆一致性
- 减少冗余记忆

### Phase 4（长期）：双向扩散检索
- 需要构建实体关系图
- 实现复杂度高
- 效果显著（提高多跳推理能力）

### Phase 5（长期）：记忆压缩
- 降低存储成本
- 提高检索效率
- 需要平衡压缩率与信息保留

---

## 五、预期效果

| 创新 | 预期提升 | 实现难度 |
|------|---------|---------|
| 时间衰减重要性 | 检索准确率+15% | 低 |
| 自适应提取窗口 | LLM成本-30% | 中 |
| 冲突检测与合并 | 记忆一致性+20% | 中 |
| 双向扩散检索 | 多跳推理+25% | 高 |
| 记忆压缩 | 存储成本-40% | 中 |

---

## 六、论文引用

1. **mem0论文**：Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory (arxiv:2504.19413v1)
   - 核心贡献：ADD/UPDATE/DELETE/NOOP算法、图记忆架构

2. **IGMiRAG论文**：IGMiRAG: Intuition-Guided Retrieval-Augmented Generation with Adaptive Mining of In-Depth Memory (arxiv:2602.07525v1)
   - 核心贡献：层次化异构超图、双向扩散算法、自适应成本控制

3. **Ebbinghaus遗忘曲线**：Hermann Ebbinghaus (1885), Memory: A Contribution to Experimental Psychology
   - 核心贡献：遗忘曲线公式 R = e^(-t/S)

---

## 七、总结

Mnemonic的算法创新基于：
1. **mem0的核心算法**（记忆提取、图记忆）
2. **IGMiRAG的创新点**（自适应控制、双向扩散）
3. **认知科学理论**（Ebbinghaus遗忘曲线）

创新方向：
1. 时间衰减重要性（理论成熟，立即实现）
2. 自适应提取窗口（降低成本）
3. 冲突检测与合并（提高一致性）
4. 双向扩散检索（提高推理能力）
5. 记忆压缩（降低存储成本）

这些创新使Mnemonic从"mem0的封装"升级为"有算法创新的记忆系统"。