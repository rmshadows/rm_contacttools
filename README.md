# ContactTools

手机通讯录整理：VCF 导入 → SQLite 编辑 → 去重审阅 → VCF 导出。

## 文档

| 文档 | 内容 |
|------|------|
| [使用说明.md](使用说明.md) | 操作步骤（0～4）、导入模式 |
| 下文 [FAQ](#faq) | 导入模式边界情形、易误解场景 |
| [docs/contacttools.md](docs/contacttools.md) | `contacttools` 包结构与模块说明 |
| [docs/dbeaver-setup.md](docs/dbeaver-setup.md) | DBeaver 连接 SQLite |
| [docs/base-setup.md](docs/base-setup.md) | LibreOffice Base + JDBC |
| [legacy/README.md](legacy/README.md) | 旧版 CSV 流程归档 |

## 流程

```bash
# 导入文件默认路径：input/contacts.vcf
python 0-reset.py              # 可选
python 1-import_vcf.py
python 2-edit_in_dbeaver.py    # 或 2-edit_in_base.py
python 3-dedup.py
python 4-export_vcf.py
```

## 目录结构

```
ContactTools/
├── 0-reset.py … 4-export_vcf.py    步骤入口
├── contacttools/                   Python 包（见 docs/contacttools.md）
├── docs/                           连接教程与模块说明
├── tests/                          单元测试
├── templates/                      VCF 格式样本（format_sample.vcf）
├── input/                          待导入 VCF（.gitignore）
├── data/                           SQLite 与运行时报告（.gitignore）
├── App/                            本地安装包，如 DBeaver .deb（.gitignore）
├── plugin/                         JDBC 驱动 jar（.gitignore）
└── legacy/                         旧版脚本
```

### 入口脚本

| 文件 | 功能 |
|------|------|
| `0-reset.py` | 清空 `data/contacts.sqlite` |
| `1-import_vcf.py` | VCF → SQLite |
| `2-edit_in_dbeaver.py` | 输出 DBeaver 连接参数 |
| `2-edit_in_base.py` | 输出 Base JDBC 连接参数 |
| `3-dedup.py` | 分步去重审阅（完全一致 / 同名 / 同号 / 其它）+ SQL 提示 |
| `4-export_vcf.py` | SQLite → VCF |

写库操作（import、merge、reset）执行前显示变更预览，输入 `y` 确认后写入。

### 导入模式概要

| 模式 | 用途 |
|------|------|
| `replace` | 首次：清空库后全量导入 |
| `append` | 增量：与库中逐条比对；完全一致则跳过，有任一字段不同则**新增**；去重靠 `3-dedup.py` |
| `upsert` | 同号合并更新 VCF 内容，否则新增 |

细则见 [使用说明.md](使用说明.md)「导入模式」一节。

### 本地目录

| 目录 | 用途 | 版本控制 |
|------|------|----------|
| `input/` | 待导入 VCF，默认 `input/contacts.vcf` | 忽略内容 |
| `data/` | `contacts.sqlite`、`review_warnings.txt` | 忽略内容 |
| `templates/` | `format_sample.vcf`，导出格式参照 | 提交样本 |
| `App/` | DBeaver 等安装包 | 忽略内容 |
| `plugin/` | `sqlite-jdbc-*.jar` | 忽略内容 |

## 数据流

```
input/contacts.vcf
    → 1-import → data/contacts.sqlite ←→ DBeaver / Base
    → 3-dedup
    → 4-export → contacts_*.vcf → 手机
```

## VCF 格式

- 版本：vCard 4.0  
- 姓名：`FN` 全名；`N:;全名;;;`  
- 样本：`templates/format_sample.vcf`  

## SQLite 速查

数据库文件：`data/contacts.sqlite`。DBeaver 中 **SQL 编辑器 → 粘贴 → Ctrl+Enter**；改完 **Ctrl+S** 提交。  
主表 `contacts`；电话 `phones`；邮箱 `emails`；宽表 `v_contacts_wide`（tel1～5）；完整 `v_contacts_full`；重复号码 `v_duplicate_phones` / `v_duplicate_phone_detail`。  
**勿改** `contacts.id`（删联系人时删 `contacts` 行即可，`phones`/`emails` 会级联删除）。

```
-- 查 ─────────────────────────────────────────
SELECT * FROM v_contacts_full ORDER BY fn_pinyin COLLATE NOCASE;
SELECT * FROM v_contacts_wide WHERE id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx';
SELECT * FROM v_duplicate_phone_detail ORDER BY dup_count DESC, fn_pinyin, number;
SELECT * FROM v_duplicate_phones ORDER BY contact_count DESC;
SELECT c.fn, p.number, p.types FROM contacts c
  JOIN phones p ON p.contact_id = c.id WHERE p.number = '13800138000';

-- 增 ─────────────────────────────────────────
INSERT INTO phones (contact_id, number, types, pref, sort_order)
  VALUES ('联系人id', '13900139000', 'CELL', 0, 2);
INSERT INTO emails (contact_id, address, types, sort_order)
  VALUES ('联系人id', 'a@example.com', 'WORK', 0);

-- 改 ─────────────────────────────────────────
UPDATE contacts SET fn = '全名', n_given = '全名', n_family = ''
  WHERE id = '联系人id';
UPDATE contacts SET org = '单位', note = '备注' WHERE id = '联系人id';
UPDATE phones SET number = '13800138000', types = 'HOME;FAX' WHERE id = 123;

-- 删 ─────────────────────────────────────────
DELETE FROM contacts WHERE id = '联系人id';          -- 删整人（推荐）
DELETE FROM phones WHERE id = 123;                   -- 只删一个号码

-- 工具 ───────────────────────────────────────
.tables                          -- sqlite3 终端：列出表
.schema contacts                 -- 看表结构
SELECT COUNT(*) FROM contacts;   -- 条数
```

命令行：`sqlite3 data/contacts.sqlite` → 输入 SQL → 以 `.quit` 退出。

## FAQ

导入模式与步骤的细则见 [使用说明.md](使用说明.md)。以下为容易误解的情形。

**`append` 怎么决定是否导入？**  
与库中每条比对**全部内容**（姓名、电话、邮箱、备注、单位等）。**完全一致** → 跳过；**任一字段不同** → **新增一条**，不修改已有行。合并、保留哪条在 `3-dedup.py` 处理。

**库里姓名写错了，手机 VCF 同号码已是正确姓名，`append` 会怎样？**  
会**新增**一条（正确名 + 同号），库中留下错名与正确名两条 → 步骤 3 `merge` 保留正确名、删掉错名。  
若不想出现两条、要直接改原记录，用 **`upsert`** 或在 DBeaver 手改。

**手机加了第三个号码，库里只有前两个，`append` 会怎样？**  
VCF 含三个号、库中只有两个 → 内容不一致 → **新增**一条（含三个号）。步骤 3 与旧记录 **merge** 合并号码。

**第二次从手机导出，想直接更新已有行、不在库里暂存 duplicate？**  
用 **`upsert`**（同号合并进原记录）。`append` 的设计是「有差异就新条 + 人工去重」。

**库里有「张三」，VCF 又来「张三」但号码不同？**  
内容不同 → **新增**。步骤 3 【B】同名待确认，人工判断是否 merge。

**同号码、其它字段也完全相同？**  
**跳过**，不写入。

**手机上已删除的联系人，库里有，`append` 会删掉吗？**  
不会。`append` 只增不删。需在 DBeaver 删除，或 `replace` 全量重建（会丢失未导出的本地整理）。

**误把 `IMPORT_MODE` 设成 `replace` 再导入会怎样？**  
清空 `contacts.sqlite` 后按 VCF 重建。DBeaver 中未导出备份的修改会丢失。写库前预览会提示将删除的条数，确认前请核对。

**`upsert` 会删掉库里多出来的电话吗？**  
不会。电话、邮箱为并集合并，按号码/地址去重，不删除库中已有项。

**DBeaver 里改过了，导出 VCF 仍是旧内容？**  
确认已保存（Ctrl+S）且连接的是 `data/contacts.sqlite`；改完再运行 `4-export_vcf.py`。

**跑 Python 脚本报 `database is locked`？**  
关闭 DBeaver 对该库的数据编辑窗口或断开连接后再执行；避免两边同时写入。

**导入手机后又出现重复联系人？**  
导入前在手机上备份；导入时按系统提示选择跳过或覆盖重复项。库内重复应先在步骤 3 处理再导出。

**找不到 VCF / Base 连不上 / 旧版 CSV 流程**  
见 [使用说明.md](使用说明.md)「常见问题」。

## Git

`.gitignore` 排除通讯录数据库、真实 VCF、CSV/XLSX、legacy 样本目录、IDE 配置及上述本地目录中的二进制文件。

提交前检查：

```bash
git status
git check-ignore -v data/contacts.sqlite input/contacts.vcf
```

`git status` 中不应出现 `.sqlite`、个人 `.vcf`、`.csv` 等敏感文件。
