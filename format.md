## 创建文件 `xxx.py`

````md
```py CREATE: xxx.py
count = 0
if __name__ == '__main__':
  print(123)
```
````

## 修改文件 `xxx.py`

````md
```diff MODIFY: xxx.py
# 定位上文
 if __name == '__main__':
-  print(123)
+  print('welcome to my world')
```
````

## 运行命令

````md
```fish EXEC
ls *
```
````

## 控制台输出内容

````md
!!! 你好呀
````

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
