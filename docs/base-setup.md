# LibreOffice Base 连接 SQLite

ContactTools 把联系人数据存放在 `data/contacts.sqlite`。LibreOffice Base 通过 JDBC 连接该文件，用于可视化查看和编辑；Python 脚本负责 VCF 导入导出、去重合并。

若更习惯 DBeaver CE（无需单独配置 JDBC jar），见 [dbeaver-setup.md](dbeaver-setup.md)。

## 1. 初始化数据库

```bash
cd <ContactTools 项目目录>
python 1-import_vcf.py
```

默认数据库路径：

```
<ContactTools 项目目录>/data/contacts.sqlite
```

也可使用 CLI：

```bash
python -m contacttools init
python -m contacttools import input/contacts.vcf --mode replace
python -m contacttools stats
```

## 2. 安装 JDBC 驱动

1. 下载 [SQLite JDBC](https://github.com/xerial/sqlite-jdbc/releases)（`sqlite-jdbc-*.jar`），可置于 `plugin/` 目录
2. LibreOffice：**工具 → 选项 → LibreOffice → 高级 → 类路径 → 添加** → 选择 jar 文件
3. 重启 LibreOffice

## 3. 新建 Base 项目并连接

1. 打开 **LibreOffice Base**
2. **创建新数据库** → 选 **连接到现有数据库**
3. 类型选 **JDBC**
4. 连接 URL（使用数据库绝对路径）：

   ```
   jdbc:sqlite:/path/to/ContactTools/data/contacts.sqlite
   ```

5. JDBC 驱动类：

   ```
   org.sqlite.JDBC
   ```

6. 测试连接 → 下一步 → 保存为 `contacts.odb`（仅保存连接配置，数据仍在 sqlite 文件）

移动硬盘挂载点变化时，需更新连接 URL，或使用软链接固定路径（参见 [dbeaver-setup.md](dbeaver-setup.md) 第 3 节）。

## 4. 推荐查看方式

| 名称 | 用途 |
|------|------|
| `contacts` | 主表：姓名、ORG、NOTE、URL、头像(BLOB) |
| `phones` | 电话子表：号码、类型、是否首选 |
| `emails` | 邮箱子表 |
| `v_contacts_wide` | 宽表视图：一行一个联系人，含 tel1～tel5 |
| `v_contacts_full` | 完整视图：一行一人，全部号码/邮箱 |
| `v_duplicate_phones` | 重复号码汇总 |
| `v_duplicate_phone_detail` | 重复号码明细（含 dup_count） |

超过 5 个号码请用 `v_contacts_full` 查看；编辑仍在 `phones` 表。

### 查重复号码

```sql
SELECT * FROM v_duplicate_phone_detail ORDER BY dup_count DESC, fn_pinyin, number;
```

### 浏览全部联系人（宽表）

```sql
SELECT id, fn, org, note, tel1, tel1_type, tel2, tel2_type
FROM v_contacts_wide
ORDER BY fn_pinyin;
```

## 5. 编辑规则

1. 勿修改 `contacts.id`（程序主键）
2. 电话增删改在 `phones` 表进行
3. 头像 BLOB 勿在 Base 中手改；通过 VCF 导入
4. Base 中保存并关闭后，再运行 `3-dedup.py`、`4-export_vcf.py`
5. 运行 `1-import_vcf.py` 或 merge 前关闭 Base，避免数据库锁

## 6. 工作流

```
手机 VCF
    → 1-import_vcf.py
    → LibreOffice Base 编辑
    → 3-dedup.py
    → 4-export_vcf.py
    → 手机
```

## 7. 常见问题

**连接失败 / 找不到驱动**

- 确认 jar 已加入 LibreOffice 类路径并重启
- 连接 URL 须为绝对路径

**Base 中修改后 export 无变化**

- 确认连接的是正确的 `contacts.sqlite`
- 表格视图修改后须保存（Ctrl+S）

**database is locked**

- 关闭 Base 后再运行 Python 脚本
