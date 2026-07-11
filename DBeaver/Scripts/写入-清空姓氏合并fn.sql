-- =============================================================================
-- ⚠️  写入操作 — 会修改数据库
--
-- 功能：清空姓氏，将姓+名合并为 fn（例：姓张名三 → fn=张三，n_family=NULL）
-- 用法：① 执行「预览」段  ② 确认后单独选中「写入」段执行  ③ Ctrl+S 提交
-- =============================================================================

-- ── 预览（只读，可先执行）────────────────────────────────────────────────────

SELECT
    id,
    fn AS 改前_fn,
    n_family || n_given AS 改后_fn,
    n_family,
    n_given
FROM contacts
WHERE n_family IS NOT NULL
  AND TRIM(n_family) <> ''
  AND n_given IS NOT NULL
  AND TRIM(n_given) <> ''
ORDER BY fn;


-- =============================================================================
-- ⚠️⚠️⚠️  以下会写入数据库 — 确认预览结果后再执行此段  ⚠️⚠️⚠️
-- =============================================================================

UPDATE contacts
SET fn = n_family || n_given,
    n_given = n_family || n_given,
    n_family = NULL
WHERE n_family IS NOT NULL
  AND TRIM(n_family) <> ''
  AND n_given IS NOT NULL
  AND TRIM(n_given) <> '';
