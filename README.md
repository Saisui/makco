# MAKCO

_专为 __氛围编程__ 打造的 __AI友好型__ markdown 格式。_

# 概述

示例 `gen.md`

创建文件 `xxx.py`

````md
```py CREATE: xxx.py
count = 0
if __name__ == '__main__':
  print(123)
```
````

修改文件 `xxx.py`
````md
```diff MODIFY: xxx.py
# 定位上文
 if __name == '__main__':
-  print(123)
+  print('welcome to my world')
```
````

运行命令
````md
```fish EXEC
ls *
```
````

控制台输出内容

````md
!!! 你好呀
````

使用

```fish
makco gen.md
```

features:
- 动作

  `CREATE` - 创建/覆盖文件

  `MODIFY` - 修改文件

  `EXEC` - 运行命令

  `ECHO` - 控制台输出消息

- 命令行使用

  敏感操作默认需要确认

  美观且完整的命令行输出

  易于使用

## 格式

### CREATE

`<file>` 为无空格且前后无空白符的文件名

````markdown
```<lang> CREATE: <file>
... 内容
```
````

### MODIFY
定义格式：
````markdown
```diff MODIFY: <file>
 <多行上文>
-<删>
+<增>
 <多行下文>
===
# 另一处要修改的
# 无歧义可以省略上文
-<删>
+<增>
# 无歧义可以省略下文
```
````

每一行第一个字符为 `前导符`，定义该行的类型：
- `-` - 删除行
- `+` - 新增行
- `~`/` ` - 上下文
- `#` - 注释行、忽略
- `===` - 分割成两处，分别修改

#### 对 AI 的容错性

- 模糊匹配:
  - 上下文允许漏行，可设定最大漏行数
  - 允许掉缩进，整体缩进少层，依然可以匹配，缩进的嵌套关系必须正确。

#### 示例

```diff MODIFY: xxx.py
# 定位上文
~def print():
# 增加文本
+  global count
+  count += 1
===
~if __name == '__main__':
-  print(123)
+  print('welcome to my world')
+  print('this is mine')
===
# 无歧义，无需上文
-  exit()
```


# 完整的复杂案例

`gen.md`

````md
创建文件
```py CREATE: xxx.py
count = 0
def print():
  hello()
if __name__ == '__main__':
  print(123)
  print('well')
  exit()
```

修改文件
```diff MODIFY: xxx.py
# 定位上文
 def print():
# 增加文本
+  global count
+  count += 1
===
 if __name == '__main__':
-  print(123)
+  print('welcome to my world')
+  print('this is mine')
===
# 无歧义，无需上文
-  exit()
```
````

## 命令行参数

| 短参数 | 长参数 | 说明 |
|--------|--------|------|
| `-c` | `--auto-run` | 命令不用确认就运行 |
| `-o` | `--skip-existing` | 跳过已存在的同名文件 |
| `-f` | `--force` | 不确认直接覆盖 |
| `-n` | `--no` | 全部拒绝（不覆盖、不运行） |
| `-y` | `--yes` | 不确认直接覆盖和运行（相当于 `-f -c`） |
| `-s` | `--silent` | 静默运行，不输出任何提示 |
| `-l <number>` | `--leeway` | 设定允许漏行数，-1 无限制，0 不允许 |
| `-d` | `--fuzzy-indent` | 开启模糊缩进匹配（默认关闭） |
| `-w` | `--no-echo` | 不显示 ECHO 消息 |
| `-r` | `--no-run` | 不运行任何命令 |
| `-M` | `--skip-modify` | 跳过所有 MODIFY 操作 |
| `-a` | `--all-confirm` | **所有操作（CREATE/COVER/EXEC/MODIFY）都必须经过确认** |
| `-h` | `--help` | 显示帮助 |
| 无参数 | | 显示帮助 |
