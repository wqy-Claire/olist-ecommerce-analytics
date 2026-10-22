"""Step 02: data profiling — understand the 9 tables before any analysis."""

import duckdb
con = duckdb.connect("olist.duckdb")

# ============================================================
print('====Q1a: orders 表总行数 vs 不重复的 order_id 个数====')
# 真实输出: total_rows = 99441, unique_orders = 99441
# 结论: 两者相等 → order_id 是 orders 表的主键（一行就是一个订单）
# ============================================================
print(con.sql("""
    SELECT count(*) AS total_rows, count(DISTINCT order_id) AS unique_orders FROM orders;
""").df())


# ============================================================
print('====Q1b: order_items 里，一个 order_id 最多出现几次====')
#⚠️
#COUNT(列名) 跳过 NULL，COUNT(*) 数所有行
# ============================================================
print(con.sql("""
    SELECT MAX(n) AS max_items_per_order
    FROM (
        SELECT COUNT(*) AS n
        FROM order_items
        GROUP BY order_id
    )
""").df())


# ============================================================
print('====Q2: 下单时间范围====')
# 真实输出: earliest = 2016-09-04 21:15:19, latest = 2018-10-17 17:30:18
# 结论: 数据跨约 2 年。第一章"GMV 异动"可锚定的候选月份就在这个范围内。
# ============================================================
print(con.sql("""
    SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders;
""").df())


# ============================================================
print('====Q3: order_delivered_customer_date 缺失多少行、占百分之几====')
#
# 【⚠️怎么在 SQL 里算 % 】
# 真实输出: null_delivered = 2965 行, 占 2.98%
# 业务含义: 没送达 = 订单被取消/在途/状态异常，
#           算配送时效时必须剔除这些行
# ============================================================
print(con.sql("""
    SELECT
        COUNT(*) FILTER (WHERE order_delivered_customer_date IS NULL) AS null_delivered,
        ROUND(COUNT(*) FILTER (WHERE order_delivered_customer_date IS NULL) * 100.0 / COUNT(*), 2) AS pct_null
    FROM orders
""").df())


# ============================================================
print('====Q4: geolocation 表 100 万行，邮编前缀有多少个不同值====')
#每个邮编平均多少行"也算出来(真正能说明重复程度的指标):
#   total_rows / unique_zips = 1000163 / 19015 ≈ 52.6 → 每个邮编平均 52.6 行坐标
print(con.sql("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT geolocation_zip_code_prefix) AS unique_zips,
        ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT geolocation_zip_code_prefix), 1) AS avg_rows_per_zip
    FROM geolocation
""").df())
# 真实输出: total_rows=1000163, unique_zips=19015,avg_rows_per_zip=52.6
# 结论: 同一个邮编被重复记录了平均 52.6 条(几乎相同的)经纬度 —— 这就是
#       地理表"虚胖"的原因。分析时按邮编聚合取一行/均值即可, 不必删全表。


# ============================================================
print('====Q5: 评论 score 分布====')
#
# 数行数用 COUNT(*), 数"某列有值的行"才用 COUNT(col)。
# COUNT(DISTINCT col) 数去重后的个数 —— Q1a/Q4
#
# 输出:
#   score=1: 11424 (11.51%)   score=2: 3151 (3.18%)   score=3: 8179 (8.24%)
#   score=4: 19142 (19.29%)   score=5: 57328 (57.78%)
# 结论: 两极分化 —— 57.78% 打 5 分, 但 11.51% 打 1 分(最低分)。
#   平均分会掩盖这个结构

# ============================================================
print(con.sql("""
    SELECT
        review_score,
        COUNT(*) AS n,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM order_reviews), 2) AS pct
    FROM order_reviews
    GROUP BY review_score
    ORDER BY review_score
""").df())


# ============================================================
print('====Q6: 支付分期数分布====')
#⚠️

# 输出: 一个 order_id 最多对应 29 笔支付
#   → 进一步确认 order_payments 与 orders 一对多; 
# 多笔支付通常是
#     "一张订单用了多种支付方式/多次扣款", 分析客单价时要用订单总额口径。
# ============================================================
print(con.sql("""
    SELECT payment_installments, count(*)
    FROM order_payments
    GROUP BY payment_installments
    ORDER BY payment_installments
""").df())

print(con.sql("""
    SELECT MAX(n) AS max_payments_per_order
    FROM (
        SELECT COUNT(*) AS n
        FROM order_payments
        GROUP BY order_id
    )
""").df())

con.close()
