#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从直播明细 xlsx 重算绩效，并把 DATA / STATS / DAILY 写回 index.html。

用法：
    python3 scripts/compute.py                        # 默认 data/2026-10.xlsx
    python3 scripts/compute.py --xlsx data/2026-11.xlsx
    python3 scripts/compute.py --period "1-20日" --date 2026-11-21

规则见 scripts/rules.md。脚本只认列名，不认列序：
需要 日期 / 主播 / 直播时长/h / 总成交额 / 广告消耗金额 这几列。
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ['韩广昊', '陈山松', '孙选博', '郭士博']   # 参与评级人员；康振东、任元丰已移出


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx', default=str(ROOT / 'data' / '2026-10.xlsx'))
    ap.add_argument('--html', default=str(ROOT / 'index.html'))
    ap.add_argument('--period', default='', help='周期标签，如 "1-27日"；留空按数据最大日自动算')
    ap.add_argument('--date', default='', help='更新日期 YYYY-MM-DD；留空取今天')
    return ap.parse_args()


def load(path):
    df = pd.read_excel(path, header=None)
    header_idx = None
    for i in range(min(5, len(df))):
        row = df.iloc[i].astype(str)
        if row.str.contains('主播').any() and row.str.contains('总成交额').any():
            header_idx = i
            break
    if header_idx is None:
        sys.exit('[compute] ❌ 没找到表头行（需同时含「主播」和「总成交额」）')
    df.columns = df.iloc[header_idx].astype(str).str.strip().tolist()
    df = df.iloc[header_idx + 1:].reset_index(drop=True)
    need = ['日期', '主播', '直播时长/h', '总成交额', '广告消耗金额']
    miss = [c for c in need if c not in df.columns]
    if miss:
        sys.exit(f'[compute] ❌ 缺列：{miss}')
    return df


def main():
    args = parse_args()
    df = load(args.xlsx)

    df['主主播'] = df['主播'].astype(str).str.split('/').str[0].str.strip()
    df = df[df['主主播'].isin(TARGETS)].copy()
    if df.empty:
        sys.exit('[compute] ❌ 过滤后没有数据，检查主播姓名是否与 TARGETS 一致')

    m = df['日期'].astype(str).str.extract(r'(\d{1,2})月(\d{1,2})日')
    df['月'] = m[0].astype(int)
    df['日'] = m[1].astype(int)
    month = int(df['月'].mode()[0])
    max_day = int(df['日'].max())
    period = args.period or f'1-{max_day}日'

    # 年份从文件名（data/2026-10.xlsx）解析，不要硬编码：跨年时硬编码会静默把标题写错。
    mfile = re.match(r'(\d{4})-(\d{1,2})', Path(args.xlsx).stem)
    year = int(mfile.group(1)) if mfile else date.today().year
    if mfile and int(mfile.group(2)) != month:
        print(f'[compute] ⚠️  文件名月份 {mfile.group(2)} 与数据月份 {month} 不一致，以数据为准')

    # 更新日期取北京时间：GitHub runner 默认 UTC，直接用 date.today() 在 UTC 16:00 之后会差一天。
    BJ = timezone(timedelta(hours=8))
    upd = args.date or datetime.now(BJ).date().isoformat()

    # ── 累计聚合 ──
    agg = df.groupby('主主播').agg(
        dur=('直播时长/h', 'sum'), gmv=('总成交额', 'sum'),
        cost=('广告消耗金额', 'sum'), shows=('主主播', 'count')).reset_index()
    agg['roi'] = agg['gmv'] / agg['cost']
    agg['sh'] = agg['gmv'] / agg['dur']

    n = len(agg)
    gmv_rank = agg.sort_values('gmv', ascending=False)['主主播'].tolist()
    sh_rank = agg.sort_values('sh', ascending=False)['主主播'].tolist()
    tot_gmv, tot_cost, tot_dur = agg['gmv'].sum(), agg['cost'].sum(), agg['dur'].sum()
    avg_roi = tot_gmv / tot_cost
    avg_dur = tot_dur / n

    def gs(name):
        i = gmv_rank.index(name)
        return 30 if i == 0 else (10 if i == n - 1 else 20)

    def rs(r):
        return 30 if r['roi'] > avg_roi else (20 if r['roi'] >= avg_roi * 0.9 else 10)

    def ss(name):
        i = sh_rank.index(name)
        return 20 if i == 0 else (5 if i == n - 1 else 15)

    def ds(r):
        return 10 if r['dur'] >= avg_dur else 5

    rows = []
    for _, r in agg.iterrows():
        d = dict(name=r['主主播'], dur=round(r['dur'], 2), gmv=int(round(r['gmv'])),
                 cost=int(round(r['cost'])), roi=round(r['roi'], 2), sh=round(r['sh'], 2),
                 shows=int(r['shows']), gmvScore=gs(r['主主播']), roiScore=rs(r),
                 shScore=ss(r['主主播']), durScore=ds(r))
        d['total'] = d['gmvScore'] + d['roiScore'] + d['shScore'] + d['durScore']
        rows.append(d)
    rows.sort(key=lambda x: (-x['total'], -x['gmv']))

    data_js = '      var DATA = [\n'
    for d in rows:
        data_js += ("      {{name:'{name}', dur:{dur}, gmv:{gmv}, cost:{cost}, roi:{roi}, "
                    "sh:{sh}, shows:{shows}, gmvScore:{gmvScore}, roiScore:{roiScore}, "
                    "shScore:{shScore}, durScore:{durScore}, total:{total}}},\n").format(**d)
    data_js = data_js.rstrip(',\n') + '\n      ];'

    stats_js = ('      var STATS = {{avgRoi:{:.2f}, avgRoi90:{:.2f}, avgDur:{:.2f}, avgDur90:{:.2f}}};'
                ).format(avg_roi, avg_roi * 0.9, avg_dur, avg_dur * 0.9)

    # ── 每日（同人当天多场合并）──
    daily = {}
    for name in TARGETS:
        sub = df[df['主主播'] == name]
        if sub.empty:
            continue
        g = sub.groupby('日').agg(dur=('直播时长/h', 'sum'), gmv=('总成交额', 'sum'),
                                  cost=('广告消耗金额', 'sum')).reset_index().sort_values('日')
        arr = []
        for _, x in g.iterrows():
            roi = x['gmv'] / x['cost']
            shp = x['gmv'] / x['dur']
            arr.append([f"{month}-{int(x['日'])}", round(float(x['dur']), 2), int(round(x['gmv'])),
                        int(round(x['cost'])), round(roi, 2), round(shp, 2)])
        daily[name] = arr
    daily_js = '      var DAILY = ' + json.dumps(daily, ensure_ascii=False, separators=(',', ':')) + ';'

    # ── 写回 HTML ──
    html = Path(args.html).read_text(encoding='utf-8')
    html, c1 = re.subn(r'      var DATA = \[.*?\n      \];', data_js, html, count=1, flags=re.S)
    html, c2 = re.subn(r'      var STATS = \{[^}]*\};', stats_js, html, count=1)
    html, c3 = re.subn(r'      var DAILY = \{.*?\};', daily_js, html, count=1, flags=re.S)
    html = re.sub(r'\d{4}年\d+月1-\d+日', f'{year}年{month}月{period}', html)
    html = re.sub(r'更新日期：\d{4}-\d\d-\d\d', f'更新日期：{upd}', html)
    Path(args.html).write_text(html, encoding='utf-8')

    print(f'[compute] 替换块 DATA={c1} STATS={c2} DAILY={c3}')
    print(f'[compute] 周期 {year}年{month}月{period} / 更新 {upd}')
    print(f'[compute] 基准 avgRoi={avg_roi:.4f} avgDur={avg_dur:.2f}')
    print('[compute] 排名：')
    for i, d in enumerate(rows, 1):
        print(f"  {i}. {d['name']} 总分{d['total']} 时长{d['dur']} GMV{d['gmv']:,} ROI{d['roi']} 单时{d['sh']} 场{d['shows']}")


if __name__ == '__main__':
    main()
