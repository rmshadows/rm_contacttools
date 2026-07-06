# ContactTools

手机通讯录整理：VCF 导入 → SQLite 编辑 → 去重审阅 → VCF 导出。

## 快速开始

```bash
pip install -r requirements.txt   # 核心功能仅用标准库

python 0-reset.py                 # 可选：清空数据库
python 1-import_vcf.py            # VCF → SQLite
python 2-edit_in_dbeaver.py       # 或 2-edit_in_base.py
python 3-dedup.py
python 4-export_vcf.py            # → contacts_YYYYMMDD_HHMMSS.vcf
```

默认输入 `input/contacts.vcf`，数据库 `data/contacts.sqlite`。  
操作步骤、导入模式细则见 **[使用说明.md](使用说明.md)**。

## 文档

| 文档 | 内容 |
|------|------|
| [使用说明.md](使用说明.md) | 步骤 0～7、导入模式、DBeaver 参考、SQL 整理语句 |
| 下文 [FAQ](#faq) | 导入模式边界情形、环境兼容 |
| [docs/contacttools.md](docs/contacttools.md) | `contacttools` 包结构 |
| [docs/dbeaver-setup.md](docs/dbeaver-setup.md) | DBeaver 连接 SQLite |
| [docs/base-setup.md](docs/base-setup.md) | LibreOffice Base + JDBC |
| [legacy/README.md](legacy/README.md) | 旧版 CSV 流程 |

## 目录结构

```
ContactTools/
├── 0-reset.py … 7-merge_contact.py   步骤入口
├── contacttools/                     Python 包
├── docs/                             连接教程与模块说明
├── tests/                            单元测试
├── templates/                        VCF 格式样本（format_sample.vcf）
├── input/                            待导入文件（.gitignore）
├── data/                             SQLite 与运行时报告（.gitignore）
├── App/                              本地安装包，如 DBeaver .deb（.gitignore）
├── plugin/                           JDBC 驱动 jar（.gitignore）
└── legacy/                           旧版脚本
```

### 入口脚本

| 文件 | 功能 |
|------|------|
| `0-reset.py` | 清空 `data/contacts.sqlite` |
| `1-import_vcf.py` | VCF → SQLite（`replace` / `append` / `upsert`） |
| `2-edit_in_dbeaver.py` | 输出 DBeaver 连接参数 |
| `2-edit_in_base.py` | 输出 Base JDBC 连接参数 |
| `3-dedup.py` | 分步去重审阅 + SQL 提示 |
| `4-export_vcf.py` | SQLite → VCF |
| `5-add_contact.py` | 从文本批量新增联系人 |
| `6-del_contact.py` | 按 `contacts.id` 删除联系人 |
| `7-merge_contact.py` | 按 id 合并联系人（交互 / 简单模式） |

写库操作（import、merge、reset、add、del）执行前显示变更预览，输入 `y` 确认后写入。

### 本地目录

| 目录 | 用途 | 版本控制 |
|------|------|----------|
| `input/` | 待导入 VCF（`contacts.vcf`）、批量新增文本（`add_contacts.txt`） | 忽略内容 |
| `data/` | `contacts.sqlite`、`review_warnings.txt`、预览报告 | 忽略内容 |
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

辅助：`5-add_contact.py` 可从 `input/add_contacts.txt` 直接写入库，无需 VCF。

## VCF 格式

- 版本：vCard 4.0
- 姓名：`FN` 全名；`N:;全名;;;`
- 样本：`templates/format_sample.vcf`

## SQLite 速查

数据库：`data/contacts.sqlite`。DBeaver 中 **SQL 编辑器 → 粘贴 → Ctrl+Enter**；改完 **Ctrl+S** 提交。

| 对象 | 说明 |
|------|------|
| `contacts` | 主表（姓名、单位、备注等） |
| `phones` / `emails` | 电话、邮箱（编辑号码在此表） |
| `v_contacts_wide` | 宽表，tel1～tel5 |
| `v_contacts_full` | 完整视图，全部号码/邮箱 |
| `v_duplicate_phones` / `v_duplicate_phone_detail` | 重复号码 |

**勿改** `contacts.id`。删整人删 `contacts` 行即可，`phones`/`emails` 级联删除。  
更多 SQL 见 [使用说明.md — SQL 整理语句](使用说明.md#sql-整理语句)。

```sql
-- 浏览
SELECT * FROM v_contacts_full ORDER BY fn_pinyin COLLATE NOCASE;
SELECT * FROM v_duplicate_phone_detail ORDER BY dup_count DESC;

-- 增删改
INSERT INTO phones (contact_id, number, types, pref, sort_order)
  VALUES ('联系人id', '13900139000', 'CELL', 0, 2);
UPDATE contacts SET fn = '全名', n_given = '全名', n_family = '' WHERE id = '联系人id';
DELETE FROM contacts WHERE id = '联系人id';
```

命令行：`sqlite3 data/contacts.sqlite`

## FAQ

导入模式与步骤细则见 [使用说明.md](使用说明.md)。以下为容易误解的情形。

**`append` 怎么决定是否导入？**  
与库中每条比对全部内容。完全一致 → 跳过；任一字段不同 → 新增一条，不修改已有行。合并靠 `3-dedup.py`。

**库里姓名错了，手机 VCF 同号码已是正确姓名？**  
`append` 会新增一条 → 步骤 3 `merge` 保留正确名。要直接改原记录用 **`upsert`** 或 DBeaver 手改。

**手机加了第三个号码，库里只有两个？**  
内容不一致 → 新增一条 → 步骤 3 与旧记录 merge。

**第二次导出想直接更新已有行、不在库里暂存 duplicate？**  
用 **`upsert`**。`append` 的设计是「有差异就新条 + 人工去重」。

**同号码、其它字段也完全相同？**  
跳过，不写入。

**手机上已删的联系人，库里有，`append` 会删吗？**  
不会。需在 DBeaver 删除，或 `replace` 全量重建。

**误设 `IMPORT_MODE = replace`？**  
清空库后按 VCF 重建；DBeaver 未导出的修改会丢失。写库前预览会提示待删条数。

**`upsert` 会删掉库里多出来的电话吗？**  
不会。电话、邮箱为并集合并，按号码/地址去重。

**DBeaver 改过了，导出仍是旧内容？**  
确认已保存（Ctrl+S）且连接的是 `data/contacts.sqlite`；再运行 `4-export_vcf.py`。

**Python 脚本报 `database is locked`？**  
关闭 DBeaver 对该库的编辑窗口或断开连接后再执行。

**DBeaver 能查视图，Python 报 `malformed database schema`？**  
视图用了较新 SQLite 语法，而系统 Python 的 SQLite 较旧（如 Debian 12 为 3.40，Debian 13 为 3.44+）。DBeaver 自带较新 JDBC 驱动故正常。请用本项目最新代码重建视图；跨机器共用库时两边代码版本保持一致。

**导入手机后又出现重复联系人？**  
导入前备份；按手机提示选择跳过或覆盖。库内重复先在步骤 3 处理再导出。

**找不到 VCF / Base 连不上 / 旧版 CSV**  
见 [使用说明.md — 常见问题](使用说明.md#常见问题)。

## Git

`.gitignore` 排除通讯录数据库、真实 VCF、CSV/XLSX 及上述本地目录中的二进制文件。

```bash
git status
git check-ignore -v data/contacts.sqlite input/contacts.vcf
```

`git status` 中不应出现 `.sqlite`、个人 `.vcf`、`.csv` 等敏感文件。
