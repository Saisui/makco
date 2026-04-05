# MAKCO

_专为 __氛围编程__ 打造的 __AI友好型__ markdown 格式。_

# 概述

让 AI 按照 [这个格式](format.md) 进行回答。


```fish
makco gen.md
```

## 功能

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

参见 [format.md](format.md)

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
````

## 命令行参数

| 短参数 | 长参数 | 说明 |
|--------|--------|------|
| `-c` | `--auto-run` | 命令不用确认就运行 |
| `-o` | `--skip-existing` | 跳过已存在的同名文件 |
| `-f` | `--force` | 不确认直接覆盖 |
| `-n` | `--no` | 全部拒绝（不覆盖、不运行） |
| `-y` | `--yes` | 不确认直接覆盖和运行（相当于 `-fc`） |
| `-s` | `--silent` | 静默运行，不输出任何提示 |
| `-l <number>` | `--leeway` | 设定允许漏行数，-1 无限制，0 不允许。默认 3 |
| `-d` | `--fuzzy-indent` | 开启模糊缩进匹配（默认关闭） |
| `-w` | `--no-echo` | 不显示 ECHO 消息 |
| `-r` | `--no-run` | 不运行任何命令 |
| `-M` | `--skip-modify` | 跳过所有 MODIFY 操作 |
| `-a` | `--all-confirm` | **所有操作（CREATE/COVER/EXEC/MODIFY）都必须经过确认** |
| `-h` | `--help` | 显示帮助 |
| 无参数 | | 显示帮助 |

# 如何使用？

直接将 [这个提示词](prompt.md) 扔给AI。

将 AI 的回答保存为 md 格式的文件，如 `ans.md`。

运行

```bash
py makco.py ans.md
```