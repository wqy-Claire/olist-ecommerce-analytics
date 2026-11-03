"""Step 03: dirty-data inventory — verify each data quality issue with SQL."""

import duckdb
from pathlib import Path

# 同 02: 用脚本所在目录定位数据库, 避免相对路径跟随终端目录产生空库
DB_PATH = Path(__file__).parent / "olist.duckdb"
con = duckdb.connect(DB_PATH)

# ============================================================
# DQ1 地理表重复：一个邮编平均多少行坐标
# 输出: total_rows=1000163, unique_zips=19015, geo_rep=52.6 (1000163/19015=52.598)
# 解读: 100 万行坐标其实只对应 1.9 万个邮编, 平均每邮编被记录 52.6 次。
#   业务假设(标注: 待验证): Olist 的地理数据来自多次抓取/多来源合并,
#   同一邮编的 GPS 采样点略有不同就被当成多条记录。
#   处理: 分析时按邮编聚合(取均值或取一行), 不需要删原始数据。
# ============================================================
print('==== DQ1: 地理表重复（每邮编平均行数）====')
print(con.sql("""
    SELECT count(*) AS total_rows, count(distinct(geolocation_zip_code_prefix)) AS unique_zips,
    round(count(*)*1.0 / count(distinct(geolocation_zip_code_prefix)),2) as geo_rep
    FROM geolocation
""").df())


# ============================================================
# DQ2 无送达时间的订单，状态都是什么
print('==== DQ2: 无送达时间订单的状态分布 ====')

#      SUM( COUNT(*) ) OVER ()
# 先把 COUNT(*) 按 GROUP BY 算出来(每组的行数),
#            然后 OVER() 对这个结果再开窗求 SUM(全部分组的总和), 当分母。
# 输出:
#   shipped 1107 (37.34%) | canceled 619 (20.88%) | unavailable 609 (20.54%)
#   invoiced 314 | processing 301 | delivered 8 (!) | created 5 | approved 2
# 解读:
#   a) 37% 是在途(shipped/invoiced/processing/created/approved) —— 数据
#      截至 2018-10, 尾部订单还没来得及送达, 业务上合理
#   b) canceled+unavailable 合计 41% —— 取消了/缺货了自然没有送达时间, 合理
#   c) ⚠️ delivered 却有 8 行缺送达时间 —— 状态与时间戳矛盾, 真脏数据,
print(con.sql("""
    SELECT order_status, count(*) AS n,
    round(COUNT(*)* 100.0 / SUM(COUNT(*)) OVER(),2) AS pct
     FROM orders
     WHERE order_delivered_customer_date IS NULL
     GROUP BY order_status
     ORDER BY n DESC
""").df())

# ============================================================
# DQ3 分期数=0 的订单详情
# 输出: 2 笔, 都是 credit_card, 金额 58.69 / 129.94(正常金额!)
# 解读: 分期数为 0 但金额正常、是信用卡支付 —— 大概率是录入默认值错误,不是"0 元订单"。
# ============================================================
print('==== DQ3: 分期数=0 的订单详情 ====')
print(con.sql("""
    SELECT order_id, payment_value, payment_type
    FROM order_payments
    WHERE payment_installments = 0
""").df())


# ============================================================
# DQ4 品类名缺失 + 翻译覆盖率
#输出:
#   4a: total=32951, 有品类名=32341, 缺失率=1.85%
#   4b: 能翻译=32328, 覆盖率=98.11%
# 解读: 品类缺失率仅 1.85%, 且 98% 能翻成英文 —— 品类维度分析可行。
#   剩余 1.9% 无品类名的商品, 归入 "unknown" 桶保留, 不删除。
# ============================================================
print('==== DQ4a: 品类名缺失 ====')
print(con.sql("""
    SELECT count(*) AS total, count(product_category_name) AS named,
    round((count(*)-count(product_category_name))*100.0/count(*),2) AS pct_missing
    FROM products
""").df())

print('==== DQ4b: 葡→英翻译覆盖率 ====')
print(con.sql("""
    SELECT count(*) AS total, count(t.product_category_name) AS translated,
    round(count(t.product_category_name)*100.0/count(*),2) AS pct_translated
    FROM products p
    LEFT JOIN category_translation t ON p.product_category_name = t.product_category_name
""").df())


# ============================================================
# DQ5 订单状态整体构成（含金额口径）
# JOIN order_items 后 canceled 从 DQ2 的 619 单变成 461 单 —— 说明约 158 个取消订单在 items 表里根本没有明细行
# 真实输出: delivered 96478 单 (97.78%), GMV 1322 万 BRL;
#   canceled 仅 0.47% (GMV 9.5 万), shipped 1.12%, 其余可忽略。
# 解读: 取消率极低 → 第一章 GMV 口径两种都站得住:
#   保守口径(只算 delivered)与宽松口径(全算)差异 <1%。
#   本项目采用 delivered-only 口径, 理由: GMV 应对应"真实成交",
#   且剔除在途订单能避开 2018-09 数据截断段的在途噪音。README 会写明。
# ============================================================
print('==== DQ5: 订单状态整体构成（数量+金额）====')
print(con.sql("""
    SELECT o.order_status, count(DISTINCT o.order_id) AS orders,
    round(count(DISTINCT o.order_id)*100.0/SUM(count(DISTINCT o.order_id)) OVER(),2) AS pct,
    round(sum(oi.price),2) AS gmv 
    FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_status 
    ORDER BY orders DESC
""").df())


# ============================================================
# DQ6 用户订单数分布（子查询套聚合）
#约 96.88% 用户只买一次
# ============================================================
print('==== DQ6: 用户订单数分布 ====')
print(con.sql("""
    SELECT n_orders, count(*) AS n_customers,
    round(count(*)*100.0/SUM(count(*)) OVER(),2) AS pct
    FROM (
        SELECT c.customer_unique_id, count(*) AS n_orders
        FROM customers c JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_unique_id
    ) AS per_customer 
    GROUP BY n_orders
    ORDER BY n_orders
""").df())


# ============================================================
# B1 月度订单量与 GMV 趋势
# COUNT(DISTINCT order_id) 防止一单多品虚高订单数;
#输出(要点, 完整月度表见 data_quality.md 附表):
#   2017-11 峰值 101 万 BRL(黑五), 2018-01~05 稳定在 84~100 万,
#   2018-06 跌至 86.5 万 (-13.2%), 2018-09/10 骤降到 16/4 单 ← 数据截断!
# 解读: 2018-09 起的"暴跌"不是业务下滑, 是数据集采集中断(DQ7),
#   第一章锚点必须选在 2018-06 的环比下跌 (或 2018-04 起的增长停滞)。
# ============================================================
print('==== B1: 月度订单量与 GMV 趋势 ====')
print(con.sql("""
    SELECT date_trunc('month', o.order_purchase_timestamp) AS month,
    count(DISTINCT o.order_id) AS orders, round(sum(oi.price),0) AS gmv
    FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY date_trunc('month', o.order_purchase_timestamp)
    ORDER BY month
""").df())

con.close()
