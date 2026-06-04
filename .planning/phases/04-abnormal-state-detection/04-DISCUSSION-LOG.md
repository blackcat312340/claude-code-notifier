# Phase 4: Abnormal-State Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 4-Abnormal-State Detection
**Areas discussed:** 不活跃检测机制, 不活跃通知规则, 什么算"仍在活跃", 异常状态路径（非不活跃）

---

## 不活跃检测机制

| Option | Description | Selected |
|--------|-------------|----------|
| 主线程定时器（pystray） | 利用 pystray 定时器在主线程周期扫描，不增加线程 | ✓ |
| 独立 daemon 线程 | 新建线程专门跑检测循环，隔离性更好 | |
| 事件驱动顺带检查 | 仅在新事件时检查，零额外开销但静默时失效 | |
| Claude 决定 | 由规划阶段选择 | |

**User's choice:** 主线程定时器（pystray）
**Notes:** 最简洁，不增加线程复杂度。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 30 秒 | 及时性最好 | |
| 60 秒（推荐） | 平衡及时性和资源消耗 | ✓ |
| 120 秒 | 最省资源 | |

**User's choice:** 60 秒
**Notes:** 推荐方案，延迟可控。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 统一 5 分钟（推荐） | 直接对应 ANOM-01 | ✓ |
| 分层阈值 | 首次 5 分钟，后续拉长 | |
| 硬编码值但预留配置点 | 5 分钟默认，代码层面不写死 | |

**User's choice:** 统一 5 分钟
**Notes:** 简单明确。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 不需要心跳（推荐） | 靠现有事件更新 last_seen | ✓ |
| 需要心跳 | hook CLI 定期发心跳包 | |
| Claude 决定 | 由规划阶段评估 | |

**User's choice:** 不需要心跳
**Notes:** 现有事件已足够证明活动。

---

## 不活跃通知规则

| Option | Description | Selected |
|--------|-------------|----------|
| 只发一次，有新事件时重置 | 简洁不打扰 | ✓ |
| 重复提醒，直到恢复 | 确保用户不遗漏 | |
| 一次提醒 + 后续升级提醒 | 首次 + 长时间不响应升级 | |

**User's choice:** 只发一次，有新事件时重置
**Notes:** 最简洁的方案。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 5 分钟专属冷却（推荐） | 不活跃独立冷却，不和常规冷却混合 | ✓ |
| 10 分钟专属冷却 | 更宽松，减少打扰 | |
| 复用现有冷却机制，统一调参 | 一个冷却系统管理所有 | |

**User's choice:** 5 分钟专属冷却
**Notes:** 独立冷却，session 级别 key。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 复用现有 IDLE 类别 | 语义一致，实现简单 | ✓ |
| 新增 STALL/INACTIVE 类别 | 语义更精确 | |
| Claude 决定 | 由规划阶段决定 | |

**User's choice:** 复用现有 IDLE 类别
**Notes:** 文案区分即可。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 静默恢复，不发通知 | 收到新事件自然表示恢复 | ✓ |
| 发恢复通知 | 告知用户 session 已恢复 | |
| Claude 决定 | 由规划阶段决定 | |

**User's choice:** 静默恢复，不发通知
**Notes:** 新事件到来就是最好的恢复信号。

---

## 什么算"仍在活跃"

| Option | Description | Selected |
|--------|-------------|----------|
| 所有已注册 session | 全部纳入监控 | ✓ |
| 只检测未 Stop 的 session | 更精准 | |
| 只检测近期活跃的 session | 忽略太老的 | |
| Claude 决定 | 由规划阶段选择 | |

**User's choice:** 所有已注册 session
**Notes:** 最全面的覆盖。

---

| Option | Description | Selected |
|--------|-------------|----------|
| Stop 后立即删除 | 最干净 | |
| Stop 后标记 + 延迟清理 | 保留短期历史 | |
| 不清理，只跳过已 Stop 的 | 保持 registry 简单 | ✓ |
| Claude 决定 | 由规划阶段决定 | |

**User's choice:** 不清理，只跳过已 Stop 的
**Notes:** 通过停止标记排除。

---

| Option | Description | Selected |
|--------|-------------|----------|
| SessionRecord 加停止标记（推荐） | 扩展字段标记停止状态 | ✓ |
| 额外检测"幽灵 session" | 检测无后续事件的 session | |
| 两者都做 | 全覆盖 | |

**User's choice:** SessionRecord 加停止标记
**Notes:** 简单有效。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 只靠 last_seen（推荐） | 任何事件更新 last_seen | ✓ |
| last_seen + 事件计数 | 追踪事件类型分布 | |
| last_seen + TCP 连接状态 | 追踪 hook CLI 连接 | |

**User's choice:** 只靠 last_seen
**Notes:** 够用，不增加复杂度。

---

## 异常状态路径（非不活跃）

| Option | Description | Selected |
|--------|-------------|----------|
| ERROR 洪水检测（推荐） | 同 session 短时间内多条 ERROR | ✓ |
| 幽灵 session 检测 | SessionStart 后无后续事件 | |
| 两者都做 | 全覆盖 | |
| Claude 决定 | 由规划阶段选择 | |

**User's choice:** ERROR 洪水检测
**Notes:** 覆盖面广，实用。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 3 条 / 2 分钟（推荐） | 灵敏 | ✓ |
| 5 条 / 5 分钟 | 更宽松 | |
| 5 条 / 2 分钟 | 折中 | |

**User's choice:** 3 条 / 2 分钟
**Notes:** 快速发现 hook 配置问题。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 用 ERROR，条件触发 | 洪水时才发，不是每个 ERROR 都发 | ✓ |
| 归入 IDLE 类别 | 异常类提醒统一用 IDLE | |
| Claude 决定 | 由规划阶段决定 | |

**User's choice:** 用 ERROR，条件触发
**Notes:** 保留 ERROR 类别语义，条件触发保留 Phase 2 D-05 意图。

---

| Option | Description | Selected |
|--------|-------------|----------|
| 10 分钟专属冷却（推荐） | 洪水问题不会立刻修复 | ✓ |
| 复用 5 分钟冷却 | 统一冷却窗口 | |
| 窗口重置，不设额外冷却 | 每次窗口重置就允许再发 | |

**User's choice:** 10 分钟专属冷却
**Notes:** 更长的冷却适合异常场景。

---

## Claude's Discretion

No areas were deferred to Claude — all decisions explicitly captured.

## Deferred Ideas

None — discussion stayed within Phase 4 scope.
