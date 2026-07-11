-- =============================================================================
-- 只读查询 — 不修改数据
-- 功能：浏览全部联系人（不限号码个数）
-- =============================================================================

SELECT id, fn, fn_pinyin, org, note, phones, phone_count, emails
FROM v_contacts_full
ORDER BY fn_pinyin COLLATE NOCASE;

-- 宽表（最多 tel1～tel5，快速浏览）
-- SELECT id, fn, fn_pinyin, org, note, tel1, tel1_type, tel2, tel3, tel4, tel5
-- FROM v_contacts_wide
-- ORDER BY fn_pinyin COLLATE NOCASE;

-- 按 contacts.id 查看
-- SELECT * FROM v_contacts_full WHERE id IN ('uuid-1', 'uuid-2');
