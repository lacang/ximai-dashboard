# AGENTS.md · 西麦直播绩效看板

给接手的 Agent 看的协作契约。读完这个文件再动手。

## 这是什么

一个纯静态的单文件看板，托管在 GitHub Pages。没有后端、没有构建步骤、没有数据库。
所有数据都以 JS 字面量内嵌在 `index.html` 里。

## 唯一正确的更新路径

```
新明细表 → 放进 data/YYYY-MM.xlsx → 跑 scripts/compute.py → 提交推送
```

**不要手改 `index.html` 里的 `var DATA` / `var STATS` / `var DAILY`。**
这三块由脚本生成，手改会在下次跑脚本时被覆盖，而且容易算错分。

## 改之前必须确认的事

1. **参与评级的名单**在 `scripts/compute.py` 的 `TARGETS` 常量里。增删人只改这一行，不要在别处硬编码。
2. **评分规则**在 `scripts/rules.md`。改规则要同时改 `compute.py` 里对应的算分函数，并在这里记一行变更。
3. **周期标签**（页面上那行「2026年10月1-27日」）由 `--period` 参数或数据最大日自动算，不要手写死。

## 提交前自检

```bash
python3 scripts/compute.py --xlsx data/YYYY-MM.xlsx
```

跑完看输出里的排名和基准值是否合理（ROI 应在 2.5–3.5 之间，总分应落在 40–100）。
如果 `替换块 DATA=0`，说明 `index.html` 的 DATA 块格式被改坏了，先修格式再继续。

## 红线

- 不把明细表传到别的服务上，不引入外部统计脚本
- 不改 `robots.txt` / `noindex`，这个仓库虽然是公开的，但不想被搜索引擎收录
- 不加后端、不加登录、不加数据库——它就是要一个能直接打开的静态页
