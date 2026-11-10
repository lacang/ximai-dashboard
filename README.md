# 西麦直播绩效看板

团队直播岗位的月度绩效排名看板。单文件 HTML，数据内嵌，没有后端，没有外部依赖。

线上：https://lacang.github.io/ximai-dashboard/

## 怎么更新数据

把新的直播明细表放进 `data/`，命名成 `YYYY-MM.xlsx`（例如 `2026-11.xlsx`），然后：

```bash
python3 scripts/compute.py --xlsx data/2026-11.xlsx
```

脚本会重算排名，把 `DATA` / `STATS` / `DAILY` 三块写回 `index.html`。提交推送后 GitHub Pages 自动更新。

也可以让 GitHub Actions 代劳：把文件推到 `data/` 就会自动跑（见 `.github/workflows/update.yml`）。

## 数据表要求

必须有的列（顺序随意，脚本按列名找）：

`日期` / `主播` / `直播时长/h` / `总成交额` / `广告消耗金额`

表头行可以在前 5 行内的任意一行。日期写成 `10月1日` 这种。

## 评分规则

见 `scripts/rules.md`。四个维度：GMV 排名、ROI、单小时产出、时长，满分 100。

参与评级的人是脚本里的 `TARGETS` 常量，改名单改那一行。

## 目录

```
index.html              看板本体（唯一产物，不要手改里面的 DATA/STATS/DAILY）
data/YYYY-MM.xlsx       原始明细
scripts/compute.py      重算脚本
scripts/rules.md        评分规则
```

## 注意

这个仓库是公开的，页面里是真实姓名和业绩数据。已加 `robots.txt` 和 `noindex`，但公开仓库仍然可被直接访问。
