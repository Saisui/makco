写一个 python，实现：

从 markdown 提取符合要求的代码块，并作出相应处理。

#### 创建文件

```<lang> CREATE: <file>
<content>
```

提取出来，创建文件 `file`。
如
```py CREATE: backend/main.py
print(123)
```

创建 `backend/main.py`

内容为
```py
print(123)
```

同名的覆盖。

将
```diff MODIFY: <file>
...
```

提取出来。
按照以下格式修改文件 file：

```diff MODIFY: <file>
@<上文>
-删
+增
@<下文>
```

每一行的 __第一个字符__ 为 __前缀__ 。
前缀必须是每一行的第一个字符！
上下文行前缀可以是任意非`-+#@\n` 的占位符，如 [ .:]
注释行前缀为 `#`
支持交错
按常识理解这个格式怎么用，怎么操作
没有歧义的时候，上下文可以省略
支持用 `/^===+/` 或 /^@@+/ 分割成两部分修改块。（废除原来的 --- ）
如
源代码
```py
# begin of file
hello()
print(666)
@loadtime(23) # 这是python的装饰器！！！
def a():
    print(55)
    name = 0
    age = 233
    gender = 0

def b():
    pass
# 省略更多
```

应用 diff

```diff MODIFY: x.py
 print(666)
# 注意下一行的行首（即前缀）是一个空格！
 @loadtime(23) # 这是python的装饰器！！！
 def a():
     print(55)
-    name = 0
+    name = 6
     age = 233
-    gender = 0
-    gender = 1
```

运行命令：

```<lang> EXEC
<command>
```

则确认是否运行命令
