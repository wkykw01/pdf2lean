# 形式化证明系统架构设计

## 核心思路

"双轨制"架构，兼顾人类阅读直觉与机器严格逻辑验证，灵感来源于 AlphaProof 等 AI 数学研究项目。

---

## 输入约束

- **格式**: 文本型 PDF（非扫描件）
- **语言**: 中文 + 数学公式（LaTeX 符号）

---

## 系统流程

### 1. 输入层
文本型 PDF 文档

### 2. 提取层
AI Agent 将 PDF 全文转化为可编译的 LaTeX

### 3. 分发层（串行：先 A 后 B）

#### 轨道 A：人机交互轨道
```
LaTeX → pdflatex 编译 → 生成 PDF 预览 → 用户核对
```
- 编译失败时，LangGraph Agent 进行 trace 追踪并自动修复
- 用户确认 PDF 正确后，才进入轨道 B

#### 轨道 B：核心逻辑轨道（三级分层节点树）
```
LaTeX 全文
  └─ LangGraph Agent 分析
       └─ 识别"最重要的一个定理"（由提示词引导）
            └─ 拆解该定理的证明结构 → 三级分层节点树
                 ├─ Level 1: 目标定理
                 ├─ Level 2: 直接依赖的引理
                 └─ Level 3: 引理所依赖的基础命题
                      └─ 每个节点包含：
                           ├─ 原文描述片段（来自 LaTeX）
                           └─ 对应 Lean 4 + Mathlib 代码
```

**Lean 验证循环（每个节点）**:
```
Lean 代码 → Lean 编译器校验 → 失败 → LangGraph Agent 迭代修复 → 重新校验
                            → 成功 → 节点标记为已验证
```

### 4. 输出层
- **输出 1**: 精美的 PDF 文档（轨道 A 产物）
- **输出 2**: 三级分层节点树 + 每节点的 Lean 4 验证代码

---

## LangGraph Agent 的两个职责

| 职责 | 触发时机 | 作用 |
|------|----------|------|
| **Trace 追踪** | LaTeX 编译失败 | 分析 pdflatex 错误日志，定位问题行，自动修复 LaTeX |
| **定理拆解** | 轨道 B 启动 | 根据提示词找到最重要的定理，递归拆解证明依赖，构建节点树 |

---

## 三级节点树结构（数据模型）

```
TheoremNode:
  id: str
  level: 1 | 2 | 3
  title: str                  # 定理/引理名称
  source_text: str            # 原文 LaTeX 片段
  lean_code: str              # 对应 Lean 4 代码
  lean_verified: bool         # 是否通过 Lean 编译
  children: List[TheoremNode] # 子节点（依赖的引理）
```

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | React |
| 后端 | FastAPI |
| Agent 框架 | LangGraph |
| LLM | 待定 |
| LaTeX 编译 | pdflatex |
| 形式化验证 | Lean 4 + Mathlib |

---

## 待讨论

1. LLM 选型（GPT-4o / Claude / 本地模型）
2. "最重要定理"的提示词策略（用户输入 or 系统自动判断）
3. Lean 迭代修复的最大轮次上限
4. 节点树的前端可视化形式（树状图 / 折叠列表 / 思维导图）
5. 节点树是否支持用户手动调整（增删节点、修改原文映射）
