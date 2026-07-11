-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：检查姓名 fn 中的空格、姓氏/名字结构异常
-- =============================================================================

-- 姓名含空格（半角 U+0020 或全角 U+3000）
SELECT id, fn, fn_pinyin, hex(fn) AS fn_hex
FROM contacts
WHERE fn LIKE '% %' OR fn LIKE '%　%'
ORDER BY fn;

-- 姓氏非空，或名字为空
SELECT id, fn, n_family, n_given
FROM contacts
WHERE n_family IS NOT NULL
   OR n_given IS NULL
   OR TRIM(n_given) = ''
ORDER BY fn;

-- 姓/名长度异常
SELECT id, fn, n_family, n_given,
       LENGTH(n_family) AS 姓长度,
       LENGTH(n_given) AS 名长度
FROM contacts
WHERE LENGTH(n_family) > 2 OR LENGTH(n_given) > 3
ORDER BY fn;
