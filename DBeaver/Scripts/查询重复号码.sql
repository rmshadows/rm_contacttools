SELECT
    p.id AS phone_id,
    c.fn,
    c.fn_pinyin,
    p.number,
    p.types,
    cnt.重复次数
FROM contacts c
JOIN phones p
    ON c.id = p.contact_id

-- 统计每个重复号码出现了几次
JOIN (
    SELECT
        number,
        COUNT(*) AS 重复次数
    FROM phones
    WHERE TRIM(number) <> ''
    GROUP BY number
    HAVING COUNT(*) > 1
) cnt
    ON p.number = cnt.number

WHERE c.id IN (
    SELECT DISTINCT p2.contact_id
    FROM phones p2
    JOIN (
        SELECT number
        FROM phones
        WHERE TRIM(number) <> ''
        GROUP BY number
        HAVING COUNT(*) > 1
    ) d
        ON p2.number = d.number
)

ORDER BY
    cnt.重复次数 DESC,
    c.fn,
    p.number,
    p.id;