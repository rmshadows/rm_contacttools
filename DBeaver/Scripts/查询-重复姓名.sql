-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：查姓名 fn 重复的联系人及其电话
-- =============================================================================

SELECT
    p.id AS phone_id,
    c.id AS contact_id,
    c.fn,
    c.fn_pinyin,
    c.org,
    c.note,
    p.number,
    p.types,
    cnt.重复次数
FROM phones p
JOIN contacts c ON p.contact_id = c.id
JOIN (
    SELECT fn, COUNT(*) AS 重复次数
    FROM contacts
    WHERE TRIM(fn) <> ''
    GROUP BY fn
    HAVING COUNT(*) > 1
) cnt ON c.fn = cnt.fn
ORDER BY cnt.重复次数 DESC, c.fn, p.number, p.id;
