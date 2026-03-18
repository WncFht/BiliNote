# Bilibili Digest Backfill Reuse And Batch BiliNote Design

## Goal

解决当前 `bilibili-up-digest` 在回填日报时的两个高优先级问题：

1. past-day 回填默认会重刷已有视频笔记，导致一次补日报退化成接近全量重算。
2. `bilinote-cli` 虽然已支持 `--jobs` 并发，但 digest 侧仍按“单视频 + 单子进程 + `capture_output`”串行调用，缺少实时可观测性与可靠恢复语义。

本设计的目标是把回填流程改成“默认复用已有 canonical note，只批量生成缺失 note”，并让批量生成具备结构化结果、日志落盘和可恢复语义。

## Scope

- 调整 `bilibili_up_digest.pipeline.run_daily_digest(...)` 的视频处理流程
- 为 digest 增加“已有 note 默认复用，刷新显式 opt-in”的策略
- 为 `bilinote-cli` 增加批量运行的结构化结果文件
- 用单次 batch CLI 调用替代 digest 当前的逐条 CLI 子进程调用
- 为 digest 侧批量调用增加 run 目录、日志文件和进度转发
- 调整日报中“失败与待补”的来源，只记录真实失败项

## Non-Goals

- 不改成 digest 直接 import `NoteGenerator`
- 不重写 canonical video note 的 frontmatter 或正文模板
- 不改变视频发现、动态抓取、日期修复和索引重建的现有业务规则
- 不在第一版引入复杂任务队列或数据库级恢复状态机

## Current Problems

### Problem 1: Existing Notes Are Refreshed During Backfill

当前流程在找到已有 note 后，仍会继续调用 `generate_markdown_fn(...)` 刷新正文，而不是直接复用已有 note。

现状：

- `find_existing_video_note(...)` 只决定“create 还是 refresh”
- 只要 `existing_path is not None`，就进入 refresh 分支
- refresh 分支仍调用 `generate_markdown_fn(item.url, "concise")`

结果：

- past-day rerun 会重复跑已有视频的下载、转写、总结链路
- 缺失 2 条、已有 14 条时，仍会把 16 条都重新送进生成链路
- 任意一条慢视频都可能阻塞整次 rerun

### Problem 2: Digest Uses Serial Single-URL CLI Calls With Poor Observability

当前 `bilinote_client.generate_bilinote_markdown(...)` 每次只接收一个 URL，并执行一次：

```bash
uv run bilinote-cli <single_url> --style concise --no-screenshot --output <tempfile>
```

现状：

- digest 在 Python 循环里逐条调用 CLI
- 每条调用默认最多卡 `900s`
- `capture_output=True` 把子进程输出都吃到内存里
- 外层看不到结构化进度，也拿不到部分成功结果

结果：

- 无法复用 `bilinote-cli --jobs`
- 一旦中途超时，外层很难知道哪些视频已完成、哪些未完成
- 恢复依赖读 vault 和查日志，不具备清晰的程序化恢复路径

## Design Summary

采用三条核心原则：

1. `existing note default reuse`
   same-day 和 past-day 都默认复用已有 note；只有显式传参时才刷新。
2. `single concurrency layer`
   并发只保留在 `bilinote-cli --jobs` 这一层，digest 自己不再套第二层线程池。
3. `manifest-driven batch execution`
   digest 不再依赖解析 CLI stdout，而是依赖 batch 运行输出的 manifest 和进度文件。

## User-Facing Behavior

### Default Behavior

默认运行 `build_daily_digest.py` 时：

- 若某个 BVID 已存在 canonical note，则直接复用
- 若某个 BVID 缺失 canonical note，则加入本次 batch 生成
- 日报总是从“已复用 + 新生成”的记录集合拼装

### Explicit Refresh

新增 `--refresh-existing` 选项。

语义：

- 默认不刷新已有 note
- 显式传 `--refresh-existing` 后，已有 note 才进入生成链路
- `--refresh-existing` 影响 same-day 与 past-day，一律一致

这样可以让回填和当日更新都具备稳定的默认行为：已有内容默认视为产物，而不是待重算任务。

## Detailed Design

### 1. Split Video Handling Into Discover / Plan / Execute / Assemble

当前 `run_daily_digest(...)` 在单个 `for item in videos` 循环中同时完成：

- 查找已有 note
- 决定 refresh/create
- 调用 CLI
- 写 canonical note
- 收集结果

这个结构需要拆开。

目标结构：

1. `discover`
   - 完成视频发现、日期修复、按天过滤、去重
   - 输出 `videos: list[NormalizedVideoItem]`
2. `plan`
   - 为每个 `item` 生成 `VideoPlanEntry`
   - 只决定 action，不做生成
3. `execute`
   - `reuse`：直接读取现有 note
   - `generate` / `refresh`：通过 batch CLI 生成 Markdown，再 canonicalize
4. `assemble`
   - 汇总 `VideoNoteRecord`
   - 写日报
   - 重建索引

### 2. Planning Model

新增内部数据结构：

```python
@dataclass
class VideoPlanEntry:
    item: NormalizedVideoItem
    tracked_up: TrackedUp
    existing_path: Path | None
    target_path: Path
    action: Literal["reuse", "generate", "refresh"]
```

规则：

- `existing_path is not None` 且未传 `--refresh-existing` -> `reuse`
- `existing_path is not None` 且传了 `--refresh-existing` -> `refresh`
- `existing_path is None` -> `generate`
- 若缺少 `published_at` 且无法定位 `target_path` -> 记录真实 failure，不进入 batch

这样 `find_existing_video_note(...)` 的职责从“决定刷新还是创建”变成“提供计划输入”。

### 3. Execution Semantics

#### `reuse`

`reuse` 不调用 `bilinote-cli`。

执行方式：

- 直接读取 `existing_path`
- 通过 `_video_record_from_path(existing_path)` 转成 `VideoNoteRecord`
- 记录执行状态为 `reused`

注意：

- `reuse` 不属于 warning，不进入日报“失败与待补”
- `reuse` 是正常成功路径

#### `generate`

`generate` 只处理缺失 note。

执行方式：

- 将所有 `action == "generate"` 的条目分批
- 每批调用一次 batch CLI
- 从 manifest 读取成功项
- 对成功项执行 canonicalization，并写入 `target_path`

#### `refresh`

`refresh` 与 `generate` 共用同一套 batch CLI 调用方式。

区别：

- `refresh` 的目标路径使用 `existing_path`
- canonicalization 时传入 `existing_markdown`
- 成功后原地覆盖已有 note

### 4. Batch CLI Contract

为 `bilinote-cli` 新增两个参数：

```bash
uv run bilinote-cli <url1> <url2> ... \
  --jobs 2 \
  --manifest-json /tmp/run/manifest.json \
  --continue-on-error \
  --output /tmp/run/output
```

#### `--manifest-json`

CLI 结束后必须写出结构化 manifest。

建议结构：

```json
{
  "started_at": "2026-03-18T20:36:38+08:00",
  "finished_at": "2026-03-18T20:38:10+08:00",
  "jobs": 2,
  "total": 2,
  "success_count": 2,
  "failure_count": 0,
  "items": [
    {
      "index": 0,
      "video_url": "https://www.bilibili.com/video/BVxxxx/",
      "status": "success",
      "output_path": "/tmp/run/output/xxx.md",
      "video_id": "BVxxxx",
      "title": "标题",
      "duration_seconds": 41.3,
      "error": null
    }
  ]
}
```

要求：

- 即使批量中出现失败，也要尽量写出完整 manifest
- digest 只依赖 manifest，不依赖 stdout 最后一行

#### `--continue-on-error`

语义：

- 某一条失败不阻断其他条继续执行
- CLI 最终可以返回非零退出码
- 但 manifest 必须包含成功项和失败项

这保证 digest 在 batch 部分失败时仍可消费部分成功结果。

### 5. Optional Progress File For Real-Time Observability

仅有最终 manifest 还不够。为了替代现在被 `capture_output` 吃掉的中间过程，新增可选进度文件：

```bash
--progress-jsonl /tmp/run/progress.jsonl
```

`progress.jsonl` 每行一个事件，例如：

```json
{"event":"batch_started","total":4,"jobs":2,"ts":"..."}
{"event":"note_started","index":0,"video_url":"...","ts":"..."}
{"event":"note_succeeded","index":0,"video_url":"...","output_path":"...","duration_seconds":31.2,"ts":"..."}
{"event":"note_failed","index":1,"video_url":"...","error":"...","ts":"..."}
{"event":"batch_finished","success_count":3,"failure_count":1,"ts":"..."}
```

digest 侧 wrapper 只做两件事：

- 子进程 stdout/stderr 落盘
- 周期性读取 `progress.jsonl` 中新增事件并转发到 digest logger

这样外层日志能看到真实进度，而不是只知道“正在创建某条视频”。

### 6. Digest Batch Wrapper

将当前：

```python
generate_bilinote_markdown(video_url: str, style: str) -> str
```

改成：

```python
generate_bilinote_batch(
    video_urls: list[str],
    *,
    style: str,
    jobs: int,
    run_dir: Path,
) -> BatchBiliNoteResult
```

新增结果结构：

```python
@dataclass
class GeneratedNote:
    video_url: str
    output_path: Path
    markdown: str
    video_id: str | None
    title: str | None

@dataclass
class GeneratedFailure:
    video_url: str
    error: str

@dataclass
class BatchBiliNoteResult:
    successes: list[GeneratedNote]
    failures: list[GeneratedFailure]
    manifest_path: Path
    progress_path: Path | None
    stdout_log_path: Path
    stderr_log_path: Path
```

run 目录约定：

```text
/tmp/bili-up-digest/<day>/<run-id>/
  manifest.json
  progress.jsonl
  stdout.log
  stderr.log
  output/
```

digest 对外日志只打印：

- batch 开始
- batch 结束
- 成功/失败统计
- manifest 与日志路径

### 7. Batching Strategy

新增 digest CLI 参数：

- `--refresh-existing`
- `--bilinote-jobs`
- `--bilinote-batch-size`

默认值：

- `refresh_existing = False`
- `bilinote_jobs = 2`
- `bilinote_batch_size = 8`

执行规则：

- 所有 `generate` + `refresh` 项按 `batch_size` 切批
- 每批调用一次 `bilinote-cli --jobs <bilinote_jobs>`
- digest 自身不再并发调多个 batch

这样可以避免双层并发放大资源占用。

### 8. Canonicalization Flow

无论 `generate` 还是 `refresh`，digest 都继续保留当前 canonicalization 逻辑：

1. 读取 batch 产出的 Markdown
2. 调用 `_canonical_video_markdown(...)`
3. 写入 vault 中的 canonical note 路径
4. 通过 `_video_record_from_path(...)` 回收记录

这意味着：

- CLI 仍然只负责“生成原始 Markdown”
- digest 继续是 canonical note 的唯一写入者
- One-Body Rule 保持不变

### 8.1 Batch Output Filename Uniqueness

batch CLI 运行时，多个 URL 会共享同一个临时 output 目录。当前 CLI 最终文件名主要来自 Markdown H1 或视频标题，这在 batch 模式下存在重名覆盖风险。

第一版要求：

- batch 输出目录中的文件名必须具备唯一性
- 推荐格式：`<video_id> <sanitized_title>.md`
- 若标题缺失，则退回 `<video_id>.md`
- manifest 中的 `output_path` 为 digest 读取产物的唯一可信来源

这样可以避免 digest 在读取 batch 产物时因为标题碰撞拿到错误文件。

### 9. Failure Semantics

当前日报把 `warnings` 和 `failures` 合并成了一个列表，导致“人为跳过刷新”这种非失败状态也会进入“失败与待补”。

新设计下需要明确区分：

- `reused`
- `generated`
- `refreshed`
- `failed`

规则：

- `reused` 不进日报失败区
- `generated` / `refreshed` 成功不进日报失败区
- 只有真正无法生成 canonical note 的项进入 `failures`

对应地，日报渲染入口应只接收真实 `failures`，不再直接使用 `[*warnings, *failures]`。

### 10. Recovery Model

恢复模型不依赖新的数据库状态机，而依赖已有 vault 产物和 batch manifest：

1. rerun 时，先扫描已有 canonical note
2. 已有 note 默认 `reuse`
3. 缺失 note 才重新进入 `generate`
4. 若某个 batch 部分成功，已写入 canonical note 的项下次直接复用

结果：

- 中途超时不会破坏已完成的工作
- rerun 成本与“缺失项数量”近似线性相关，而不是与“整天视频数量”线性相关

## Compatibility

### `bilinote-cli`

为避免破坏现有用法：

- 不移除当前 stdout 打印 output path 的行为
- `--manifest-json` / `--progress-jsonl` / `--continue-on-error` 为新增可选参数

### `bilibili-up-digest`

兼容策略：

- 原有单条 `generate_bilinote_markdown(...)` 可暂时保留，供非 batch 场景或过渡期调用
- 新 pipeline 优先使用 batch wrapper

## Validation

### Unit Tests

- `pipeline`:
  - 已有 note + 默认策略 => `reuse`
  - 已有 note + `--refresh-existing` => `refresh`
  - 缺失 note => `generate`
  - `reuse` 不触发 `generate_markdown_fn`
  - `reused` 不进入日报失败区

- `bilinote_client`:
  - batch wrapper 正确构造 CLI 命令
  - 正确读取 manifest
  - 正确转发 progress 事件
  - 子进程非零退出但 manifest 有部分成功时，能返回部分成功结果

- `bilinote-cli`:
  - `--manifest-json` 生成完整 manifest
  - `--continue-on-error` 允许部分成功
  - `--progress-jsonl` 输出开始/成功/失败/结束事件

### Integration Tests

- 14 条已有 + 2 条缺失的 backfill rerun，只生成 2 条，不刷新已有 14 条
- batch 中一条失败时，其他条仍能写入 canonical note
- rerun 后日报视频数来自“复用 + 新生成”的并集

### Manual Validation

- 使用真实 past-day 样本运行一次 backfill
- 验证：
  - 已有 note 未重刷
  - 缺失 note 通过 batch CLI 生成
  - run 目录内有 manifest / progress / logs
  - 日报写出成功
  - “失败与待补” 只包含真实失败项

## Implementation Order

1. 先拆分 pipeline 的 `plan / execute` 结构，并落地 `reuse` 默认策略
2. 再为 `bilinote-cli` 增加 `manifest-json` 与 `continue-on-error`
3. 最后让 digest wrapper 切到 batch CLI，并接入 `progress-jsonl`

这样第一步单独完成时，就已经能消除“回填默认全量重刷”的主要风险；后两步再解决并发利用率和可观测性问题。
