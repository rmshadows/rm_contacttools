-- =============================================================================
-- ⚠️  写入操作 — 会修改数据库
--
-- 功能：按 contacts.id 删除整人（phones / emails 级联删除）
-- 用法：① 将 ${contact_ids} 改为具体 uuid，或配置 DBeaver 绑定变量
--       ② 执行「预览」段  ③ 确认后单独选中「写入」段执行  ④ Ctrl+S 提交
--
-- 也可用 Python：python 6-del_contact.py <id1> [<id2> ...]
-- =============================================================================

-- ── 预览（只读，可先执行）────────────────────────────────────────────────────

-- 该联系人是否还有号码
SELECT p.*
FROM phones p
WHERE p.contact_id IN (${contact_ids});

-- 待删除的联系人
SELECT id, fn, fn_pinyin, org, note
FROM contacts
WHERE id IN (${contact_ids});

-- 不用变量时示例：
-- WHERE id IN ('uuid-1', 'uuid-2');


-- =============================================================================
-- ⚠️⚠️⚠️  以下会写入数据库 — 确认预览结果后再执行此段  ⚠️⚠️⚠️
-- =============================================================================

DELETE FROM contacts
WHERE id IN (${contact_ids});

-- DELETE FROM contacts WHERE id IN ('uuid-1', 'uuid-2');
