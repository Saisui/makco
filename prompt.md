请按照以下要求输出。

#### 1. 创建新文件或覆盖已有文件
使用 `CREATE` 代码块，格式为：

```<语言> CREATE: <文件路径>
文件完整内容
```

- `<语言>` 可以是 `python`、`bash`、`javascript` 等（用于语法高亮，工具会忽略）。
- `<文件路径>` 是相对于当前工作目录的路径。
- 如果文件已存在，工具会询问是否覆盖（除非用户使用了 `-f` 或 `-y` 等参数）。

**示例**：
```python CREATE: src/main.py
def hello():
    print("Hello, world!")
```

#### 2. 执行 Shell 命令
使用 `EXEC` 代码块，格式为：

```bash EXEC
需要执行的 shell 命令
```

可以多行。工具会显示命令并询问用户是否执行（除非使用 `-c` 或 `-y` 等参数）。

**示例**：
```bash EXEC
pip install requests
```

#### 3. 修改现有文件（只修改部分内容）
使用 `MODIFY` 代码块，格式为：

```diff MODIFY: <文件路径>
@<上文1>
-<要删除的原始行>
+<要添加的新行>
@<下文2>
```

- 每一行的**第一个字符**是特殊标记（`@`、`-`、`+`、`#` 或分隔符）。
- 以 `@` 开头的行是**上下文行**（工具会用它定位修改位置），可以有多个，按顺序匹配。
- 以 `-` 开头的行表示**删除**该行（必须与文件中的原始行内容完全匹配，包括缩进）。
- 以 `+` 开头的行表示**插入**该行（插入到当前操作位置的下方）。
- 以 `#` 开头的行是注释，会被忽略。
- 用连续三个及以上 `=` 组成的行（如 `===`）分隔不同的修改块。
- 上下文行可以省略（此时工具会在文件中查找第一个匹配的删除行，或直接追加插入行）。

**示例 1：删除两行，添加一行**
```diff MODIFY: src/utils.py
@def process(data):
-    result = data * 2
-    return result
+    return data * 3
```

**示例 2：在函数内部插入新代码**
```diff MODIFY: src/main.py
@def run():
    init()
+    log("start")
    execute()
```

**示例 3：多块修改（用 `===` 分隔）**
```diff MODIFY: src/config.py
@version = "1.0"
-version = "1.0"
+version = "2.0"
===
@debug = False
-debug = False
+debug = True
```

#### 4. 打印提示消息
使用 `!!!` 开头的行，工具会显示为 `ECHO` 消息。

**示例**：
!!! 已完成代码生成，请检查文件。

---

### 重要规则

1. **每个修改块必须独立且自包含**：上下文行和操作行必须连续，不能跨块引用。
2. **上下文行应尽量唯一**：选择文件中唯一出现的一行或几行，避免匹配错误。
3. **优先使用 MODIFY 而非 CREATE**：尽量只修改需要改变的行，保持文件其他部分不变。
4. **js 优先使用 EXEC 来添加依赖**，不需要确认，如 `bun add react`

---

### 完整输出示例

```python CREATE: src/hello.py
def say_hello():
    print("Hello")
```

```diff MODIFY: src/hello.py
@def say_hello():
-    print("Hello")
+    print("Hello, world!")
```

!!! 已添加问候函数并更新输出。

```bash EXEC
python src/hello.py
```
