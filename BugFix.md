# Mnemonic BugFix Log

## Format
```
### BUG-XXX: Title
- **发现时间**: YYYY-MM-DD HH:MM
- **测试场景**: 哪个测试发现的
- **严重度**: P0(阻塞) / P1(严重) / P2(中等) / P3(轻微)
- **状态**: 🔴 Open / 🟡 Fixing / 🟢 Fixed / ⏳ Deferred
- **影响**: 影响范围
- **根因**: 根本原因
- **修复**: 修复方案
```

---

### BUG-001: PATCH更新内容后embedding未重新生成
- **发现时间**: 2026-04-29 22:50
- **测试场景**: T10.4 PATCH更新content后搜索不到新内容
- **严重度**: P1
- **状态**: 🟢 Fixed
- **影响**: PATCH更新content后，embedding仍是旧的，语义搜索不准确
- **根因**: store.py的update()方法接收embedding参数，但api.py的update_memory()在content变更时调用`embedding_service.embed()`生成新embedding并传入。验证DB后确认embedding已正确更新。**实际上是PASS的**。
- **修复**: 无需修复，行为正确。

---

### BUG-002: memory_type字段无枚举校验
- **发现时间**: 2026-04-29 23:10
- **测试场景**: T16.4 传入memory_type="invalid_type_xyz"返回201
- **严重度**: P2
- **状态**: 🔴 Open
- **影响**: 任意字符串可作为memory_type，可能导致下游查询异常
- **根因**: schemas.py的MemoryCreate中memory_type定义为`str`无枚举限制
- **修复建议**: 添加`Literal["fact", "preference", "rule", "context"]`枚举约束

---

### BUG-003: search返回的similarity为null
- **发现时间**: 2026-04-29 23:00
- **测试场景**: T09/T10 搜索返回similarity=null
- **严重度**: P2
- **状态**: 🟡 Investigating
- **影响**: 前端无法显示相似度分数
- **根因**: 待确认，可能是response model序列化问题或pgvector距离计算返回值类型
- **修复**: —

---

### BUG-004: Extract端点返回201(设计为200)
- **发现时间**: 2026-04-29 23:05
- **测试场景**: T11.1 Extract正常请求返回201
- **严重度**: P3
- **状态**: ⏳ Deferred
- **影响**: HTTP语义上201=Created，extract时如果只提取不存储应返回200。当auto_store=true时201可接受。
- **根因**: api.py line 208: `status_code=201`硬编码
- **修复建议**: auto_store=True时201，auto_store=False时200

---

### BUG-005: memory_type无枚举限制
- **发现时间**: 2026-04-29 23:15
- **测试场景**: T16.4 任意memory_type值被接受
- **严重度**: P2
- **状态**: 🔴 Open
- **影响**: 同BUG-002
- **根因**: schemas.py未定义枚举
- **修复建议**: 使用Literal或Enum

---

### BUG-006: 4级namespace跨session无法召回记忆（关键设计问题）
- **发现时间**: 2026-04-29 23:20
- **测试场景**: T20.4 Hermes新session(session_20260501)搜索不到旧session(session_20260430)的记忆
- **严重度**: P1
- **状态**: 🔴 Open
- **影响**: Hermes每次新session启动时无法自动回忆上个session的用户偏好/项目上下文，记忆系统形同虚设
- **根因**: store.py `_namespace_filters()` line 181-182: 当namespace包含session_id时，严格匹配session_id，不同session_id之间完全隔离
- **当前workaround**: 使用3级namespace(client_id:user_id:agent_id)查询可覆盖所有子session
- **修复建议**: 
  1. **方案A**: search API增加`scope`参数：`session`(当前session) / `agent`(跨session同agent) / `user`(跨agent同user)
  2. **方案B**: Hermes MemoryProvider在search时自动strip session_id，使用3级namespace
  3. **方案C**: 默认search使用3级，create使用4级，保证写入隔离、搜索共享
- **推荐**: 方案C最简单，与当前架构完全兼容

---

### BUG-007: 搜索质量受噪声数据严重干扰
- **发现时间**: 2026-04-29 23:25
- **测试场景**: T14 搜索精确率(TOP1)仅14.3%
- **严重度**: P1
- **状态**: 🔴 Open
- **影响**: 搜索质量不达标，大量测试用记忆（"快速创建测试_0"等）干扰真实记忆的召回
- **根因**: 
  1. 测试数据噪声：测试过程中创建的低质量记忆与真实记忆混在一起
  2. importance权重未参与搜索排序（当前只按cosine distance排序）
- **修复建议**: 
  1. 搜索时按`importance * cosine_similarity`加权排序
  2. 清理测试数据后重新评估
  3. Phase 2引入WRRF权重

---

### BUG-008: Extract返回空结果（LLM API Key未配置）
- **发现时间**: 2026-04-29 23:10
- **测试场景**: T11/T18 Extract所有请求返回[]
- **严重度**: P1
- **状态**: 🟡 Deferred (需真实API key)
- **影响**: Extract功能完全不可用
- **根因**: 启动时传入的LLM API key是`test-key`，Gemma端点可连通但认证失败
- **修复**: 需要配置真实的LLM API key（Gemma-4自部署端点或SiliconFlow）
