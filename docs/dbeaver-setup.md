# DBeaver CE 连接 SQLite

ContactTools 的联系人数据在 **`data/contacts.sqlite`**。  
**DBeaver Community Edition** 可直接打开 SQLite，无需像 LibreOffice Base 那样单独配置 JDBC 驱动 jar，适合在电脑上浏览、筛选、改表。

Python 脚本负责 VCF 导入导出；DBeaver 负责**可视化编辑**（与 Base 二选一即可，不要两边同时改）。

LibreOffice Base 说明见 [`base-setup.md`](base-setup.md)。

---

## 1. 安装 DBeaver CE

- 官网：<https://dbeaver.io/download/>
- 选 **Community Edition**（免费）
- Linux 可用 `.deb` / 解压版 / `flatpak install io.dbeaver.DBeaverCommunity`

安装后首次启动即可，**不用**额外下载 SQLite 驱动（DBeaver 自带）。

---

## 2. 先准备好数据库

在项目目录执行（若已跑过 `1-import_vcf.py` 可跳过）：

```bash
cd <ContactTools 项目目录>
python 1-import_vcf.py
```

默认数据库文件：

```
ContactTools/data/contacts.sqlite
```

---

## 3. 新建 SQLite 连接

1. 打开 DBeaver → **数据库 → 新建数据库连接**（或左上角插头图标）
2. 选择 **SQLite** → 下一步
3. **Path（路径）** → **浏览**，选中：

   ```
   .../ContactTools/data/contacts.sqlite
   ```

4. 连接名示例：`ContactTools`
5. **测试连接** → 应显示 Connected → **完成**

### 移动硬盘 / 路径会变时

DBeaver 里保存的是**当时选中的绝对路径**。硬盘挂载点变了会连不上，任选其一：

**做法 A — 每次改连接路径**  
右键连接 → **编辑连接** → 重新浏览新的 `contacts.sqlite` 路径。

**做法 B — 固定软链接（推荐，只配一次）**

插盘后执行（将源路径替换为当前 `contacts.sqlite` 绝对路径）：

```bash
ln -sf /path/to/ContactTools/data/contacts.sqlite ~/ContactTools-contacts.sqlite
```

DBeaver 中连接路径固定为：

```
~/ContactTools-contacts.sqlite
```

换挂载点后**只重跑一条 `ln -sf`**，DBeaver 连接不用改。

---

## 4. 表和视图说明

展开连接 → **Tables** / **Views**：

| 名称 | 用途 |
|------|------|
| `contacts` | 主表：姓名 `fn`、拼音排序键 `fn_pinyin`、`org`、`note`、`url`、头像 `photo`(BLOB) |
| `phones` | **电话子表**：号码、`types`（如 CELL/HOME/秘书科）、`pref`、`sort_order` |
| `emails` | 邮箱子表 |
| `v_contacts_wide` | 宽表视图：一行一人，**仅 tel1～tel5**，快速浏览 |
| `v_contacts_full` | **完整视图**：一行一人，`phones` / `emails` 列含**全部**号码与邮箱（分号分隔） |
| `v_duplicate_phones` | 重复号码汇总（每个号码一行，含涉及的联系人数） |
| `v_duplicate_phone_detail` | **重复号码明细**：每条 `phones` 行一行，含姓名、`dup_count`（重复次数） |
| `import_batches` | 导入历史（只读参考） |
| `merge_history` | 合并历史（只读参考） |

**超过 5 个号码的联系人**：用 **`v_contacts_full`** 查看全部号码；编辑仍在 **`phones` 表**。

---

### 5.1a 浏览全部联系人（完整视图，不限号码个数）

```sql
SELECT id, fn, fn_pinyin, org, note, phones, phone_count, emails
FROM v_contacts_full
ORDER BY fn_pinyin COLLATE NOCASE;
```

`phones` 列格式示例：`13800138000 (CELL); 010-1234 (HOME)`。

---

### 5.1 浏览全部联系人（宽表，最多 5 个号码）

右键 `v_contacts_wide` → **查看数据**，或 SQL 编辑器：

```sql
SELECT id, fn, fn_pinyin, org, note, tel1, tel1_type, tel2, tel2_type, tel3, tel4, tel5
FROM v_contacts_wide
ORDER BY fn_pinyin COLLATE NOCASE;
```

DBeaver 点列头排序仍是 Unicode 序；**按拼音请用上面 SQL**，或点 `fn_pinyin` 列头排序。

在 DBeaver 里改了 `fn` 后，运行 `python 2-edit_in_dbeaver.py` 会同步 `fn_pinyin`（也可 import/merge 时自动更新）。

### 5.2 查某人的所有号码

```sql
SELECT c.fn, p.number, p.types, p.pref, p.sort_order
FROM contacts c
JOIN phones p ON p.contact_id = c.id
WHERE c.fn LIKE '%关键字%'
ORDER BY p.sort_order;
```

### 5.3 查重复号码

**汇总**（每个号码一行）：

```sql
SELECT * FROM v_duplicate_phones
ORDER BY contact_count DESC;
```

**明细**（涉及重复的每个联系人、每条号码一行；`dup_count` = 该号码在库中出现总次数）：

```sql
SELECT phone_id, fn, fn_pinyin, number, types, dup_count
FROM v_duplicate_phone_detail
ORDER BY dup_count DESC, fn_pinyin COLLATE NOCASE, number, phone_id;
```

或菜单：**SQL 编辑器 → 新建 SQL 脚本**，粘贴后 **Ctrl+Enter** 执行。

### 5.4 改数据

1. 打开表（如 `contacts` 或 `phones`）→ **数据** 标签
2. 双击单元格修改
3. 改完后 **Ctrl+S** 或工具栏 **保存**（Commit）
4. 未保存时导航栏常有「未提交变更」提示

**增删电话行**：在 `phones` 表数据视图底部 **+** 新增一行，填 `contact_id`、 `number`、 `types`（如 `CELL`）、 `pref`（0/1）、 `sort_order`（0 起）。

**删整人**：先删 `phones` / `emails` 中该 `contact_id` 的行，再删 `contacts`（外键级联在 schema 里已配置，删 `contacts` 会连带删子表，但 DBeaver 有时需确认）。

---

## 6. 编辑规则（重要）

1. **不要改 `contacts.id`** — 程序主键；改了会导致电话 orphaned 或导出错乱
2. **`phones.types`** — 多个类型用分号，与程序一致，如 `HOME;FAX` 或单个 `CELL`
3. **头像 `photo`** — 不要在 DBeaver 里手改 BLOB；用 VCF 导入带头像的联系人
4. **改完再跑 Python**：
   - DBeaver **保存并提交**后，可关闭连接或保持只读
   - 再运行 `python 3-dedup.py`、`python 4-export_vcf.py`
   - 跑 `1-import_vcf.py` / 合并前，**关闭 DBeaver 对该库的写入**，避免锁库

---

## 7. 与 ContactTools 四步流程配合

| 步骤 | 脚本 | DBeaver 角色 |
|------|------|----------------|
| 1 | `1-import_vcf.py` | 导入后可在 DBeaver **刷新**（F5）看数据 |
| 2 | `2-edit_in_dbeaver.py` | 输出连接参数；在 DBeaver 中编辑 |
| 3 | `3-dedup.py` | 重复列表与 DBeaver 里 `v_duplicate_phones` 一致 |
| 4 | `4-export_vcf.py` | 改完并保存后再导出 VCF 到手机 |

```
手机 VCF → 1-import → DBeaver 编辑 → 3-dedup → 4-export → 手机
```

---

## 8. 常见问题

**测试连接失败 / file not found**

- 路径是否指向当前挂载的移动硬盘
- 是否尚未运行 `1-import_vcf.py`（库不存在）
- 软链接方案：检查 `~/ContactTools-contacts.sqlite` 是否指向正确文件

**改了数据但 export 没变化**

- DBeaver 是否 **Ctrl+S 提交**
- 是否连的是同一个 `contacts.sqlite`（别连到副本）

**database is locked**

- 关闭 DBeaver 中该库的数据编辑窗口，或断开连接后再跑 Python
- 不要 DBeaver 与 Python `import` 同时写入

**宽表只有 5 个号码**

- 仅 `v_contacts_wide` 视图限制；真实数据在 `phones` 表，条数不限

**中文乱码**

- SQLite 为 UTF-8；DBeaver 连接属性里字符集一般默认即可

---

## 9. DBeaver 与 LibreOffice Base 怎么选

| | DBeaver CE | LibreOffice Base |
|---|------------|------------------|
| 配置难度 | 低（选文件即可） | 中（JDBC + jar） |
| 编辑体验 | 表格 + SQL 强 | 表单/表格式 |
| 移动硬盘 | 改路径或软链接 | 同样需绝对路径/软链接 |
| 与项目关系 | 外部工具 | 可存 `.odb` 连接项目 |

**只用一个即可**；习惯 SQL 和表格筛选的，用 DBeaver 往往更省事。
