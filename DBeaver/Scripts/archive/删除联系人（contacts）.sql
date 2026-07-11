--查询contacts有，但是phones为空的联系人
SELECT
    c.id,
    c.fn,
    c.fn_pinyin
FROM contacts c
LEFT JOIN phones p
    ON c.id = p.contact_id
WHERE p.contact_id IS NULL
ORDER BY c.fn;

-- 检查有无关联号码
SELECT *
FROM phones
WHERE contact_id IN (
    'e70c120e-6fe1-4758-8e97-3e7bc6de8d6b',
    '2659c41f-5e7b-4ad7-9a2c-fa4b31e02c4e'
);

-- 删除前预览
SELECT *
FROM contacts
WHERE id IN (
    'e70c120e-6fe1-4758-8e97-3e7bc6de8d6b',
    '2659c41f-5e7b-4ad7-9a2c-fa4b31e02c4e'
);

-- 删除
DELETE FROM contacts
WHERE id IN (
    'e70c120e-6fe1-4758-8e97-3e7bc6de8d6b',
    '2659c41f-5e7b-4ad7-9a2c-fa4b31e02c4e'
);