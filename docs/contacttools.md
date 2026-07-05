# contacttools 模块说明

Python 包路径：`contacttools/`。入口脚本与 `python -m contacttools` 均调用此包。

## 目录结构

```
contacttools/
├── __init__.py          版本号
├── __main__.py          python -m contacttools 入口
├── cli.py               子命令：init / reset / import / export / merge / stats / dedup
│
├── models/
│   ├── __init__.py
│   └── contact.py       Contact、Phone、Email 数据类
│
├── store/
│   ├── schema.sql       表、视图、索引定义
│   └── database.py      SQLite 连接、CRUD、重复号码查询
│
├── vcf/
│   ├── template.py      VCF 4.0 导出常量（VERSION、PRODID、字段顺序）
│   ├── parser.py        VCF 文本 → Contact 列表
│   ├── writer.py        Contact 列表 → VCF 文本
│   └── fold.py          RFC 折行（PHOTO base64）
│
├── normalize/
│   ├── phone.py         号码去非数字、去 +86 前缀
│   └── name.py          姓名统一为全名（FN + N:;全名;;;）
│
└── ops/
    ├── import_vcf.py    VCF 导入（replace / append / upsert）
    ├── export_vcf.py    导出 VCF
    ├── merge.py         联系人合并、重复号码分组
    ├── reset.py         数据库重置
    ├── contact_merge.py 同号码字段合并规则
    ├── name_review.py   同名分组、格式警告、审阅报告
    ├── plan.py          写库前变更预览
    ├── confirm.py       终端确认（y/N）
    └── diff.py          联系人字段差异描述
```

## 模块职责

### models

| 类型 | 说明 |
|------|------|
| `Contact` | 主记录：id、fn、n_family、n_given、org、note、phones、emails 等 |
| `Phone` | 号码、类型标签、是否首选、排序 |
| `Email` | 邮箱地址与类型 |

### store

| 文件 | 说明 |
|------|------|
| `schema.sql` | `contacts`、`phones`、`emails` 表 |
| `views.sql` | `v_contacts_wide`、`v_contacts_full`、`v_duplicate_phones`、`v_duplicate_phone_detail` |
| `database.py` | 默认路径 `data/contacts.sqlite`；`save_contact`、`list_contacts`、`duplicate_phone_report` 等 |

### vcf

| 文件 | 说明 |
|------|------|
| `parser.py` | 解析 vCard 2.1/3.0/4.0；处理折行、多 TEL、PHOTO data URI |
| `writer.py` | 按 `templates/format_sample.vcf` 格式输出 |
| `template.py` | `VERSION=4.0`，`PRODID=ez-vcard 0.12.1` |

### normalize

导入流水线中在写入数据库前执行：

1. `phone.normalize_contact_phones` — 号码规范化  
2. `name.normalize_to_fullname` — 姓名合并为全名  

### ops

| 模块 | 写库 | 说明 |
|------|------|------|
| `import_vcf` | 是 | 导入前 `build_import_plan` + 确认；见下方三种模式 |
| `export_vcf` | 否 | 仅读库、写 VCF 文件 |
| `merge` | 是 | 合并前 `build_merge_plan` + 确认 |
| `reset` | 是 | 删除 sqlite 并重建 schema |
| `name_review` | 否 | 生成 `data/review_warnings.txt` |

### import_vcf 三种模式

**replace** — 清空库，写入 VCF 全部条目。

**append** — 与库中全部记录比对内容。完全一致则跳过；任一字段不同则**新增一条**（不修改已有行）。去重、merge 在 `3-dedup.py` 人工完成。

**upsert** — 号码已在库中则调用 `merge_contact_fields` 合并进原记录；否则新增。合并规则：`fn`/`org`/`note`/`url` 取 VCF 非空值否则保留库值；电话/邮箱并集去重；VCF 含 `photo` 则更新。

## 调用关系

```
1-import_vcf.py
    → ops.import_vcf
        → vcf.parser
        → normalize.phone / normalize.name
        → ops.plan / ops.confirm
        → store.database

4-export_vcf.py
    → ops.export_vcf
        → store.database
        → normalize.name
        → vcf.writer

3-dedup.py
    → ops.name_review
    → ops.merge（可选）
```

## 命令行

```bash
python -m contacttools init
python -m contacttools reset [-y]
python -m contacttools import <vcf> --mode replace|append|upsert [-y]
python -m contacttools export -o <path>
python -m contacttools merge --keep <id> --drop <id...> [-y]
python -m contacttools stats
python -m contacttools dedup
```

`-y` 跳过写库确认，仅用于脚本化场景。

## 测试

| 文件 | 覆盖 |
|------|------|
| `tests/test_roundtrip.py` | parser → import → export → parser |
| `tests/test_name_review.py` | 姓名规范化、同名分组 |
| `tests/test_confirm.py` | replace 模式变更预览 |

运行：

```bash
PYTHONPATH=. python -m unittest discover -s tests
```
