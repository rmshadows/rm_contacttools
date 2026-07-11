-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：检查电话格式异常、空号码、596 前缀待修正
-- =============================================================================

-- 格式疑似异常（非大陆手机/固话/400/800/95/96 常见模式）
SELECT
    c.fn AS 姓名,
    p.id AS phone_id,
    p.number AS 电话,
    p.types AS 类型,
    p.pref,
    p.sort_order,
    CASE
        WHEN
            (LENGTH(p.number) = 11 AND p.number GLOB '1[3-9][0-9]*')
            OR (p.number GLOB '0*' AND LENGTH(p.number) BETWEEN 10 AND 12)
            OR (p.number GLOB '400*' AND LENGTH(p.number) = 10)
            OR (p.number GLOB '800*' AND LENGTH(p.number) = 10)
            OR (p.number GLOB '95*' AND LENGTH(p.number) BETWEEN 5 AND 8)
            OR (p.number GLOB '96*' AND LENGTH(p.number) BETWEEN 5 AND 8)
        THEN ''
        ELSE '异常'
    END AS 标记
FROM phones p
JOIN contacts c ON c.id = p.contact_id
WHERE p.contact_id IN (
    SELECT contact_id
    FROM phones
    WHERE NOT (
        (LENGTH(number) = 11 AND number GLOB '1[3-9][0-9]*')
        OR (number GLOB '0*' AND LENGTH(number) BETWEEN 10 AND 12)
        OR (number GLOB '400*' AND LENGTH(number) = 10)
        OR (number GLOB '800*' AND LENGTH(number) = 10)
        OR (number GLOB '95*' AND LENGTH(number) BETWEEN 5 AND 8)
        OR (number GLOB '96*' AND LENGTH(number) BETWEEN 5 AND 8)
    )
)
ORDER BY c.fn, p.sort_order, p.id;

-- 电话为空
SELECT
    p.id AS phone_id,
    c.fn AS 姓名,
    p.number AS 电话,
    p.types AS 类型
FROM phones p
LEFT JOIN contacts c ON c.id = p.contact_id
WHERE p.number IS NULL OR TRIM(p.number) = ''
ORDER BY c.fn, p.sort_order;

-- 596 开头、待补 0 前缀（修正见 写入-号码596补0前缀.sql）
SELECT p.id AS phone_id, c.fn, p.number, p.types
FROM phones p
JOIN contacts c ON p.contact_id = c.id
WHERE p.number LIKE '596%'
ORDER BY p.number;
