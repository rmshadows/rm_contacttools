-- ContactTools 视图（由 database._migrate_views 加载；init_schema 时重建）

DROP VIEW IF EXISTS v_duplicate_phone_detail;
DROP VIEW IF EXISTS v_duplicate_phones;
DROP VIEW IF EXISTS v_contacts_full;
DROP VIEW IF EXISTS v_contacts_wide;

-- 宽表：一行一人，tel1～tel5，快速浏览
CREATE VIEW v_contacts_wide AS
SELECT
    c.id,
    c.fn,
    c.fn_pinyin,
    c.org,
    c.title,
    c.note,
    c.url,
    CASE WHEN c.photo IS NOT NULL THEN 1 ELSE 0 END AS has_photo,
    p1.number AS tel1, p1.types AS tel1_type, p1.pref AS tel1_pref,
    p2.number AS tel2, p2.types AS tel2_type,
    p3.number AS tel3, p3.types AS tel3_type,
    p4.number AS tel4, p4.types AS tel4_type,
    p5.number AS tel5, p5.types AS tel5_type
FROM contacts c
LEFT JOIN phones p1 ON p1.contact_id = c.id AND p1.sort_order = 0
LEFT JOIN phones p2 ON p2.contact_id = c.id AND p2.sort_order = 1
LEFT JOIN phones p3 ON p3.contact_id = c.id AND p3.sort_order = 2
LEFT JOIN phones p4 ON p4.contact_id = c.id AND p4.sort_order = 3
LEFT JOIN phones p5 ON p5.contact_id = c.id AND p5.sort_order = 4;

-- 完整：一行一人，全部号码/邮箱（分号分隔，不限个数）
CREATE VIEW v_contacts_full AS
SELECT
    c.id,
    c.fn,
    c.fn_pinyin,
    c.org,
    c.title,
    c.note,
    c.url,
    CASE WHEN c.photo IS NOT NULL THEN 1 ELSE 0 END AS has_photo,
    (
        SELECT GROUP_CONCAT(item, '; ')
        FROM (
            SELECT p.number || ' (' || p.types || ')' AS item
            FROM phones p
            WHERE p.contact_id = c.id
            ORDER BY p.sort_order, p.id
        )
    ) AS phones,
    (
        SELECT COUNT(*)
        FROM phones p
        WHERE p.contact_id = c.id
    ) AS phone_count,
    (
        SELECT GROUP_CONCAT(item, '; ')
        FROM (
            SELECT e.address || ' (' || e.types || ')' AS item
            FROM emails e
            WHERE e.contact_id = c.id
            ORDER BY e.sort_order, e.id
        )
    ) AS emails
FROM contacts c;

-- 重复号码汇总：每个号码对应多少不同联系人
CREATE VIEW v_duplicate_phones AS
SELECT
    number,
    COUNT(DISTINCT contact_id) AS contact_count,
    GROUP_CONCAT(contact_id, ',') AS contact_ids
FROM phones
WHERE TRIM(number) <> ''
GROUP BY number
HAVING contact_count > 1;

-- 重复号码明细：每条 phone 行一行，含姓名与重复次数
CREATE VIEW v_duplicate_phone_detail AS
SELECT
    p.id AS phone_id,
    c.id AS contact_id,
    c.fn,
    c.fn_pinyin,
    p.number,
    p.types,
    cnt.dup_count
FROM contacts c
JOIN phones p ON c.id = p.contact_id
JOIN (
    SELECT number, COUNT(*) AS dup_count
    FROM phones
    WHERE TRIM(number) <> ''
    GROUP BY number
    HAVING COUNT(*) > 1
) cnt ON p.number = cnt.number;
