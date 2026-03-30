def modify(orig: str, diff: str) -> str:
    """
    将 diff 格式的修改应用到源文本 orig，返回修改后的完整文本。

    diff 格式规则：
    - 每行第一个字符为前缀，标识行类型。
    - 前缀 '#' 为注释行，忽略。
    - 前缀 '-' 或 '+' 为操作行，操作符后的内容（保留原样）作为操作内容。
    - 前缀为连续两个以上 '=' 或 '@' 的行是分隔符，用于分割多个修改块。
    - 其他任何字符（包括空格、点、冒号等）作为上下文行，去掉第一个字符后的内容作为上下文。
    - 上下文行用于定位修改位置（连续子串匹配，忽略行首尾空白）。
    - 操作按顺序应用于上下文匹配块之后的位置。
    - 无上下文时，通过第一个删除行定位（精确匹配）或直接追加到末尾。
    """
    # 辅助类
    class DiffBlock:
        def __init__(self, context, ops):
            self.context = context   # list of context lines (content without prefix)
            self.ops = ops           # list of (op, line)

    # 解析 diff 文本为 DiffBlock 列表
    def parse_diff_blocks(diff_text: str):
        lines = diff_text.splitlines()
        blocks = []
        current_context = []
        current_ops = []
        in_block = False

        for raw_line in lines:
            line = raw_line.rstrip('\n')
            if not line:
                continue
            first_char = line[0]

            # 分隔符：连续两个以上相同的 '=' 或 '@'
            if first_char in ('=', '@') and len(line) >= 2 and all(c == first_char for c in line):
                if in_block:
                    blocks.append(DiffBlock(current_context, current_ops))
                    current_context = []
                    current_ops = []
                    in_block = False
                continue

            # 注释行
            if first_char == '#':
                continue

            # 操作行
            if first_char in ('-', '+'):
                if not in_block:
                    in_block = True
                content = line[1:]   # 保留原样（含前导空格）
                current_ops.append((first_char, content))
                continue

            # 上下文行
            if not in_block:
                in_block = True
            content = line[1:]   # 去掉前缀字符
            current_context.append(content)

        if in_block:
            blocks.append(DiffBlock(current_context, current_ops))

        return blocks

    # 查找上下文位置（连续子串匹配，忽略首尾空白）
    def find_context_position(lines, context_lines):
        if not context_lines:
            return None
        n = len(lines)
        m = len(context_lines)
        trimmed_ctx = [c.strip() for c in context_lines]
        for i in range(n - m + 1):
            match = True
            for j in range(m):
                if trimmed_ctx[j] not in lines[i + j].strip():
                    match = False
                    break
            if match:
                return i
        return None

    # 应用所有修改块
    def apply_blocks(orig_lines, blocks):
        lines = orig_lines[:]  # 复制，每个元素是字符串（不含换行符）
        success = False
        for block in blocks:
            if not block.ops:
                continue

            # 定位起始位置
            start_idx = None
            if block.context:
                pos = find_context_position(lines, block.context)
                if pos is None:
                    continue  # 上下文未找到，跳过此块
                start_idx = pos + len(block.context)
            else:
                # 无上下文：通过删除行定位或追加
                del_lines = [op[1] for op in block.ops if op[0] == '-']
                if del_lines:
                    target = del_lines[0]
                    found = -1
                    for i, line in enumerate(lines):
                        if line == target:
                            found = i
                            break
                    if found == -1:
                        continue
                    start_idx = found
                else:
                    start_idx = len(lines)

            # 应用操作
            before = lines[:start_idx]
            after = lines[start_idx:]
            i = 0
            ok = True
            for op, content in block.ops:
                if op == '-':
                    if i < len(after) and after[i] == content:
                        del after[i]
                    else:
                        ok = False
                        break
                elif op == '+':
                    after.insert(i, content)  # 插入时不带换行符
                    i += 1
            if not ok:
                continue
            lines = before + after
            success = True

        return lines, success

    orig_lines = orig.splitlines()
    blocks = parse_diff_blocks(diff)
    new_lines, _ = apply_blocks(orig_lines, blocks)
    return '\n'.join(new_lines)