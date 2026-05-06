# Mnemonic Algorithm Validation - Final Report

**Date**: 2026-05-06  
**Version**: v0.3.0  
**Validation Method**: Real Session Data + LLM Extraction

---

## Executive Summary

使用真实session数据和LLM提取进行验证，结果如下：

| 维度 | 结果 | 目标 | 状态 |
|------|------|------|------|
| **D1 Extraction F1** | 62.22% | ≥75% | ✗ FAIL |
| **D2 Conflict Accuracy** | 0% | ≥90% | ✗ FAIL |
| **D3 Noise Rate** | 0% | ≤10% | ✓ PASS |

---

## Validation Methods Comparison

### 三种验证方法对比

| 方法 | D1 F1 | D2 Accuracy | D3 Noise Rate | 说明 |
|------|-------|-------------|---------------|------|
| **合成数据 + 启发式** | 82.42% ✓ | 100% ✓ | 0% ✓ | 人工构造，匹配简单 |
| **真实数据 + 启发式** | 12.50% ✗ | 0% ✗ | 0% ✓ | 真实对话，启发式不足 |
| **真实数据 + LLM** | 62.22% ✗ | 0% ✗ | 0% ✓ | LLM提取，匹配策略待优化 |

---

## Detailed Analysis

### D1: Extraction Quality

**结果**: F1 = 62.22%

**数据**:
- Total Expected: 22 memories
- Total Extracted: 23 memories
- Correct Matches: 14 memories
- Precision: 60.87%
- Recall: 63.64%

**问题分析**:

1. **Expected vs Extracted内容差异**

   Expected (人工总结):
   ```
   "Hermes PluginManager 自动扫描 4 个来源：Bundled、User、Project、pip entry_points"
   ```

   Extracted (LLM原始):
   ```
   "Hermes PluginManager 的插件加载机制是通过自动扫描 bundled、user、project 和 pip entry_points 四个来源实现的"
   ```

   差异：表达方式不同，但语义相同

2. **匹配策略局限**

   当前匹配：关键词重叠 ≥20% OR 实体匹配 ≥2个
   
   未匹配案例：
   - Expected: "Mnemonic API需要x-namespace header"
   - Extracted: "API调用时需要在请求头中添加x-namespace参数"
   - 关键词重叠：低（"API", "x-namespace"）
   - 但语义完全一致

**改进方向**:

1. **使用Embedding相似度**：计算Expected和Extracted的向量相似度
2. **使用LLM评判**：让LLM判断两者是否语义等价
3. **放宽Expected定义**：接受多种表达方式

### D2: Conflict Resolution

**结果**: Accuracy = 0%

**问题分析**:

冲突场景：
```
旧记忆: "Vector搜索L1是13.3%"
新记忆: "Vector搜索L1是53.3%"
```

算法检测: `NONE`（未检测到冲突）

原因：
- `_is_update()` 函数依赖特定模式（"lives in", "works at"）
- 数值更新模式未覆盖

**改进方向**:

扩展冲突检测模式：
```python
# 数值更新模式
if re.search(r'\d+%?', content_1) and re.search(r'\d+%?', content_2):
    # 检查是否同一主题
    if topic_similarity(content_1, content_2) > 0.7:
        return ConflictType.UPDATE
```

### D3: Robustness

**结果**: Noise Rate = 0% ✓

**验证通过**:
- "好的" → 0 memories extracted ✓
- "谢谢" → 0 memories extracted ✓

LLM成功过滤无意义的短对话。

---

## LLM Extraction Quality

### 提取数量统计

| Conversation | Expected | Extracted | Match |
|--------------|----------|-----------|-------|
| real_001 | 2 | 2 | 2 ✓ |
| real_002 | 2 | 2 | 1 |
| real_003 | 1 | 1 | 1 ✓ |
| real_004 | 2 | 2 | 1 |
| real_005 | 3 | 3 | 2 |
| real_006 | 1 | 2 | 1 |
| real_007 | 2 | 2 | 0 |
| real_008 | 2 | 2 | 1 |
| real_009 | 2 | 2 | 2 ✓ |
| real_010 | 1 | 1 | 1 ✓ |
| real_011 | 2 | 3 | 1 |
| real_conflict_001 | 1 | 1 | 1 ✓ |
| real_conflict_002 | 1 | 0 | 0 |

**提取准确率**: 23/22 = 104.5% (略微过度提取)

### 自适应窗口效果

| Mode | Count | Avg Extracted |
|------|-------|---------------|
| fast (m=5, s=5) | 11 | 1.9 |
| standard (m=10, s=10) | 2 | 1.5 |

复杂对话使用standard窗口，简单对话使用fast窗口。

---

## Recommendations

### 短期改进（算法层）

1. **扩展冲突检测模式**
   - 数值更新：`\d+%?` vs `\d+%?`
   - 状态变更：`是 X` vs `是 Y`
   - 时间更新：`\d{4}` vs `\d{4}`

2. **优化匹配策略**
   - 降低关键词重叠阈值至15%
   - 增加同义词匹配
   - 增加数字/实体精确匹配

### 中期改进（评估层）

1. **使用Embedding相似度**
   ```python
   similarity = cosine_similarity(embed(expected), embed(extracted))
   if similarity > 0.8:
       match = True
   ```

2. **使用LLM评判**
   ```python
   prompt = f"这两条记忆是否表达相同信息？\nA: {expected}\nB: {extracted}"
   is_match = llm.judge(prompt)
   ```

### 长期改进（数据层）

1. **重新定义Expected**
   - 不用人工精炼总结
   - 直接使用LLM提取结果作为Ground Truth
   - 或提供多个Accepted答案

---

## Conclusion

### 核心发现

1. ✅ **LLM提取有效**：成功提取23条记忆，数量接近预期
2. ✅ **噪声过滤有效**：LLM成功过滤无意义对话
3. ✗ **匹配策略不足**：关键词匹配无法识别语义等价
4. ✗ **冲突检测不足**：数值更新等模式未覆盖

### 下一步

1. **优先级1**：扩展冲突检测模式（数值、状态、时间）
2. **优先级2**：使用Embedding相似度进行匹配
3. **优先级3**：重新定义Expected数据集

---

**Report Generated**: 2026-05-06 22:10:00  
**LLM Used**: Gemma-4 (120.25.63.187:9119)  
**Validation Status**: PARTIAL PASS (D3 only)