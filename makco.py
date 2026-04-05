#!/usr/bin/env python3
"""
从 Markdown 中提取并执行 CREATE、EXEC、MODIFY 代码块和 ECHO 消息。
支持多种命令行参数控制交互行为，使用 RGB 颜色输出。
"""

import os
import sys
import argparse
import subprocess
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

# ===================== 颜色工具 =====================
class Color:
    """RGB 颜色生成器，预定义常用颜色常量。"""
    RESET = '\033[0m'

    @staticmethod
    def bg(r: int, g: int, b: int) -> str:
        return f'\033[48;2;{r};{g};{b}m'

    @staticmethod
    def fg(r: int, g: int, b: int) -> str:
        return f'\033[38;2;{r};{g};{b}m'

    # 预定义常量（背景+前景）
    CREATE = bg(0, 128, 0) + fg(255, 255, 255)
    COVER  = bg(173, 255, 47) + fg(0, 0, 0)
    EXEC   = bg(0, 100, 200) + fg(255, 255, 255)
    ECHO   = bg(0, 180, 180) + fg(255, 255, 255)
    WARN   = bg(255, 200, 0) + fg(0, 0, 0)
    MODIFY = bg(128, 0, 128) + fg(255, 255, 255)
    GRAY   = fg(128, 128, 128)

# ===================== 打印机 =====================
class Printer:
    """统一输出打印机，处理颜色和静默模式。"""
    def __init__(self, silent: bool):
        self.silent = silent

    def _write(self, text: str) -> None:
        if not self.silent:
            sys.stdout.write(text)
            sys.stdout.flush()

    def _prefix(self, prefix: str, color: str) -> None:
        self._write(color + prefix + Color.RESET + ' ')

    def warn(self, message: str) -> None:
        self._prefix(' WARN ', Color.WARN)
        self._write(Color.GRAY + message + Color.RESET + '\n')

    def exec_cmd(self, *commands: str) -> None:
        if len(commands) == 1:
            self._prefix(' EXEC ', Color.EXEC)
            self._write(Color.GRAY + commands[0] + Color.RESET + '\n')
        else:
            self._prefix(' EXEC ', Color.EXEC)
            self._write('\n')
            for cmd in commands:
                self._write(Color.GRAY + cmd + Color.RESET + '\n')

    def echo(self, message: str) -> None:
        self._prefix(' ECHO ', Color.ECHO)
        self._write(Color.GRAY + message + Color.RESET + '\n')

    def modify(self, filepath: str) -> None:
        self._prefix(' MODIFY ', Color.MODIFY)
        self._write(Color.GRAY + filepath + Color.RESET + '\n')

    def cover(self, filepath: str) -> None:
        self._prefix(' COVER ', Color.COVER)
        self._write(Color.GRAY + filepath + Color.RESET + '\n')

    def create(self, filepath: str) -> None:
        self._prefix(' CREATE ', Color.CREATE)
        self._write(Color.GRAY + filepath + Color.RESET + '\n')

    def skipped(self, text: str = " (skipped)") -> None:
        self._write(Color.GRAY + text + Color.RESET + '\n')

    def prompt(self, prefix: str, color: str, target: str, question: str) -> None:
        self._prefix(prefix, color)
        self._write(Color.GRAY + target + Color.RESET + f' - {question} (y/n) ')

# ===================== 选项封装 =====================
class Options:
    """封装命令行参数及策略。"""
    def __init__(self, args: argparse.Namespace):
        self.file = args.file
        self.auto_exec = args.auto_run
        self.skip_existing = args.skip_existing
        self.force_overwrite = args.force
        self.auto_yes = args.yes
        self.auto_no = args.no
        self.silent = args.silent
        self.no_echo = args.no_echo
        self.no_run = args.no_run
        self.skip_modify = args.skip_modify
        self.all_confirm = args.all_confirm
        self.leeway = args.leeway
        self.fuzzy_indent = args.fuzzy_indent   # 新增

        # 解决冲突
        if self.auto_yes and self.auto_no:
            self.auto_no = False
        if self.auto_yes:
            self.auto_exec = True
            self.force_overwrite = True
            self.skip_existing = False
        if self.auto_no:
            self.auto_exec = False
            self.force_overwrite = False
            self.skip_existing = True
        if self.no_run:
            self.auto_exec = False
        if self.all_confirm:
            self.auto_yes = False
            self.auto_no = False
            self.auto_exec = False
            self.force_overwrite = False
            self.skip_existing = False

    def ask_yes_no(self, printer: Printer, prompt: str = "", no_prompt: bool = False) -> bool:
        """交互式确认，使用当前选项。"""
        if self.silent:
            return True
        if self.auto_yes:
            return True
        if self.auto_no:
            return False

        while True:
            try:
                if no_prompt:
                    answer = input().strip().lower()
                else:
                    answer = input(prompt + " (y/n): ").strip().lower()
            except KeyboardInterrupt:
                sys.exit(0)
            if answer in ('y', 'yes'):
                return True
            if answer in ('n', 'no'):
                return False
            if answer in ('q', 'quit', 'exit'):
                sys.exit(0)

# ===================== 辅助类：带缩进的行 =====================
class IndentLine:
    """存储原始行、内容（去除前导空格）和缩进空格数。"""
    def __init__(self, raw_line: str):
        self.raw = raw_line.rstrip('\n')
        # 计算前导空格数
        stripped = self.raw.lstrip(' ')
        self.indent = len(self.raw) - len(stripped)
        self.content = stripped

    def __repr__(self):
        return f"IndentLine(indent={self.indent}, content={self.content})"

# ===================== 抽象操作处理器 =====================
class ActionHandler(ABC):
    """所有操作的基类。"""
    def __init__(self, printer: Printer, options: Options):
        self.printer = printer
        self.options = options

    @abstractmethod
    def handle(self, target: Optional[str], content: str) -> None:
        pass

# ===================== 具体操作处理器 =====================
class CreateHandler(ActionHandler):
    """处理 CREATE 块。"""
    def handle(self, filepath: str, content: str) -> None:
        dirname = os.path.dirname(filepath)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        force = self.options.force_overwrite
        skip = self.options.skip_existing

        # -a 模式先询问
        if self.options.all_confirm:
            exists = os.path.exists(filepath)
            if exists:
                self.printer.prompt(' WARN ', Color.WARN, filepath, 'Overwrite?')
            else:
                self.printer.prompt(' CREATE ', Color.CREATE, filepath, 'Create?')
            if not self.options.ask_yes_no(self.printer, no_prompt=True):
                self.printer.skipped()
                return
            force = True
            skip = False

        if os.path.exists(filepath):
            if skip:
                self.printer.create(filepath)
                self.printer.skipped(" (skipped, file exists)")
                return
            if force:
                self._write_file(filepath, content)
                self.printer.cover(filepath)
                return
            # 普通覆盖询问
            self.printer.prompt(' WARN ', Color.WARN, filepath, 'Overwrite?')
            if self.options.ask_yes_no(self.printer, no_prompt=True):
                self._write_file(filepath, content)
                self.printer.cover(filepath)
            else:
                self.printer.skipped()
        else:
            self._write_file(filepath, content)
            self.printer.create(filepath)

    @staticmethod
    def _write_file(filepath: str, content: str) -> None:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

class ExecHandler(ActionHandler):
    """处理 EXEC 块。"""
    def handle(self, command_str: str, _: Optional[str] = None) -> None:
        lines = command_str.splitlines()
        self.printer.exec_cmd(*lines if len(lines) > 1 else lines)

        run = False
        if self.options.no_run:
            run = False
        elif self.options.all_confirm:
            run = self.options.ask_yes_no(self.printer, "Run this command?")
        elif self.options.auto_yes or self.options.auto_exec:
            run = True
        elif self.options.auto_no:
            run = False
        else:
            run = self.options.ask_yes_no(self.printer, "Run this command?")

        if run:
            try:
                subprocess.run(command_str, shell=True, check=False)
            except Exception as e:
                sys.stderr.write(f"Error executing command: {e}\n")
        else:
            self.printer.skipped()

class ModifyHandler(ActionHandler):
    """处理 MODIFY 块，支持模糊缩进匹配。"""
    def handle(self, filepath: str, content: str) -> None:
        if self.options.skip_modify:
            self.printer.modify(filepath)
            self.printer.skipped(" (skipped by -M)")
            return

        if self.options.all_confirm:
            self.printer.prompt(' MODIFY ', Color.MODIFY, filepath, 'Apply?')
            if not self.options.ask_yes_no(self.printer, no_prompt=True):
                self.printer.skipped()
                return

        blocks = self._parse_diff_blocks(content)
        if not blocks:
            self.printer.modify(filepath)
            self.printer.skipped(" (no valid modifications)")
            return

        self.printer.modify(filepath)
        self._apply_modify(filepath, blocks)

    def _parse_diff_blocks(self, diff_text: str) -> List['DiffBlock']:
        """解析 diff 文本，返回 DiffBlock 列表。"""
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

            # 分隔符：连续两个以上 = 或 @
            if first_char in ('=', '@') and len(line) >= 2 and all(c == first_char for c in line):
                if in_block:
                    blocks.append(DiffBlock(current_context, current_ops))
                    current_context = []
                    current_ops = []
                    in_block = False
                continue

            if first_char == '#':
                continue

            if first_char in ('-', '+'):
                if not in_block:
                    in_block = True
                op = first_char
                # 保留操作符后的原始内容（包括前导空格）
                content = line[1:]   # 不要 lstrip，保留缩进
                current_ops.append((op, content))
                continue

            if not in_block:
                in_block = True
            current_context.append(line)

        if in_block:
            blocks.append(DiffBlock(current_context, current_ops))
        return blocks

    # ---------- 模糊缩进匹配核心 ----------
    def _normalize_lines(self, raw_lines: List[str]) -> List[IndentLine]:
        """将原始行列表转换为 IndentLine 对象列表。"""
        return [IndentLine(line) for line in raw_lines]

    def _match_context_with_indent(self, target_lines: List[IndentLine], context_lines: List[IndentLine], leeway: int) -> Optional[Tuple[int, int, int]]:
        """
        在 target_lines 中查找顺序匹配 context_lines 的位置。
        如果 self.options.fuzzy_indent 为 True，则允许所有行的缩进整体偏移同一个值。
        返回 (start_idx, end_idx, indent_offset) 或 None。
        """
        if not context_lines:
            return None

        n = len(target_lines)
        m = len(context_lines)

        # 预处理 context 的内容和缩进
        context_content = [c.content for c in context_lines]
        context_indents = [c.indent for c in context_lines]

        for start in range(n):
            # 检查第一个上下文行是否匹配（内容包含）
            if context_content[0] not in target_lines[start].content:
                continue

            # 尝试匹配后续行，允许跳行（leeway）
            cur = start
            matched = 1
            # 记录偏移量（如果模糊缩进开启，需要计算）
            offset = None
            if self.options.fuzzy_indent:
                offset = target_lines[start].indent - context_indents[0]
            for idx in range(1, m):
                max_next = cur + 1 + leeway if leeway != -1 else n
                upper = min(max_next, n)
                found = -1
                for j in range(cur + 1, upper):
                    # 内容匹配
                    if context_content[idx] in target_lines[j].content:
                        # 缩进检查
                        if self.options.fuzzy_indent:
                            # 要求缩进差相同
                            if target_lines[j].indent - context_indents[idx] != offset:
                                continue
                        else:
                            # 严格模式：缩进必须完全相等
                            if target_lines[j].indent != context_indents[idx]:
                                continue
                        found = j
                        break
                if found == -1:
                    break
                cur = found
                matched += 1

            if matched == m:
                if self.options.fuzzy_indent:
                    return (start, cur, offset)
                else:
                    return (start, cur, 0)  # offset 0
        return None

    def _find_deletion_line(self, lines: List[IndentLine], del_content: str, context_offset: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """
        查找第一个完全匹配删除行的位置（内容匹配，缩进考虑偏移）。
        如果 context_offset 不为 None，则要求目标行缩进 = 删除行原缩进 + offset。
        否则（无上下文时），要求缩进完全相等。
        返回 (index, actual_indent) 或 None。
        """
        # 删除行内容（去掉操作符后的字符串，保留原始缩进）
        # del_content 是操作符后的原始字符串，可能包含前导空格
        del_line = IndentLine(del_content)  # 注意：del_content 可能包含前导空格，IndentLine 会正确解析
        for i, line in enumerate(lines):
            if line.content == del_line.content:
                if context_offset is not None:
                    if line.indent == del_line.indent + context_offset:
                        return (i, line.indent)
                else:
                    if line.indent == del_line.indent:
                        return (i, line.indent)
        return None

    def _adjust_insert_line(self, insert_content: str, base_indent: int) -> str:
        """
        根据基准缩进调整插入行的缩进。
        insert_content 是操作符后的原始字符串（可能已有缩进）。
        调整策略：将插入行的缩进改为 base_indent + (原缩进 - 上下文第一个匹配行的缩进？)
        更合理：假设插入行在 diff 中的缩进相对于上下文有固定的偏移，我们应保持该偏移量。
        但这里简化：如果开启了模糊缩进，我们使用上下文匹配得到的 offset，将插入行的缩进设置为 base_indent。
        由于插入行可能本身有缩进，我们保留其相对偏移？实际需求不明确，我们采用：保留插入行自身的缩进，但整体加上 offset。
        """
        if not self.options.fuzzy_indent:
            return insert_content
        # 解析插入行的原始缩进
        ins_line = IndentLine(insert_content)
        new_indent = base_indent + ins_line.indent  # 相对偏移保持不变？
        # 重新构造行：空格 + 内容
        return ' ' * new_indent + ins_line.content

    # ---------- 修改应用 ----------
    def _find_context_position(self, lines: List[str], context_lines: List[str]) -> Optional[Tuple[int, int, int]]:
        """兼容旧接口，内部调用模糊匹配。"""
        target = self._normalize_lines(lines)
        context = self._normalize_lines(context_lines)
        return self._match_context_with_indent(target, context, self.options.leeway)

    def _apply_modify(self, filepath: str, blocks: List['DiffBlock']) -> bool:
        """应用修改块，支持模糊缩进。"""
        if not os.path.exists(filepath):
            self.printer.warn(f"{filepath} - file does not exist, skipping")
            return False

        with open(filepath, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
        # 转换为 IndentLine 列表（便于操作）
        lines = self._normalize_lines(raw_lines)

        success = False
        for block in blocks:
            if not block.ops:
                continue

            # 1. 定位起始位置
            start_idx = None
            indent_offset = 0  # 用于调整插入行的缩进
            if block.context:
                # 有上下文：使用模糊匹配
                pos = self._match_context_with_indent(lines, self._normalize_lines(block.context), self.options.leeway)
                if pos is None:
                    self.printer.warn(f"{filepath} - context not found, skipping block")
                    continue
                start_idx, end_idx, indent_offset = pos
                start_idx = end_idx + 1  # 从最后一个上下文行的下一行开始
            else:
                # 无上下文：查找第一个删除行或直接追加
                del_ops = [op for op in block.ops if op[0] == '-']
                if del_ops:
                    # 找到第一个删除行
                    del_raw = del_ops[0][1]  # 原始字符串（含缩进）
                    found = self._find_deletion_line(lines, del_raw, None)
                    if found is None:
                        self.printer.warn(f"{filepath} - deletion line not found, skipping block")
                        continue
                    start_idx, _ = found
                else:
                    # 只有增加行，追加到末尾
                    start_idx = len(lines)

            # 2. 应用操作（在 start_idx 之后）
            # 注意：lines 是 IndentLine 列表，我们需要在修改后重新构建字符串
            # 为了方便，我们操作原始行列表？但为了保持缩进调整，我们操作 IndentLine 列表，最后再转回字符串。
            # 更简单：我们直接操作原始行列表，但根据 indent_offset 调整插入行的缩进。
            # 因为我们需要保持 lines 的原始类型，这里我们使用原始行列表（字符串）进行操作，但缩进调整需要额外计算。
            # 重构：我们使用原始字符串列表，但插入时根据 indent_offset 调整。
            raw_before = raw_lines[:start_idx]
            raw_after = raw_lines[start_idx:]
            i = 0
            ok = True
            for op, raw_content in block.ops:
                if op == '-':
                    if i < len(raw_after):
                        # 删除当前行（需要匹配内容，考虑缩进）
                        target_line = raw_after[i].rstrip('\n')
                        # 解析目标行
                        target_indent = IndentLine(target_line)
                        del_line = IndentLine(raw_content)
                        # 检查匹配
                        if target_indent.content == del_line.content:
                            if self.options.fuzzy_indent:
                                # 要求缩进差等于 indent_offset
                                if target_indent.indent - del_line.indent == indent_offset:
                                    del raw_after[i]
                                else:
                                    self.printer.warn(f"{filepath} - indent mismatch for deletion line: expected {del_line.indent + indent_offset}, got {target_indent.indent}")
                                    ok = False
                                    break
                            else:
                                if target_indent.indent == del_line.indent:
                                    del raw_after[i]
                                else:
                                    self.printer.warn(f"{filepath} - indent mismatch for deletion line: expected {del_line.indent}, got {target_indent.indent}")
                                    ok = False
                                    break
                        else:
                            self.printer.warn(f"{filepath} - expected line '{del_line.content}' not found")
                            ok = False
                            break
                    else:
                        self.printer.warn(f"{filepath} - no line to delete")
                        ok = False
                        break
                elif op == '+':
                    # 插入行，需要调整缩进
                    insert_line = raw_content
                    if self.options.fuzzy_indent:
                        # 根据 indent_offset 调整缩进
                        ins = IndentLine(insert_line)
                        new_indent = ins.indent + indent_offset
                        if new_indent < 0:
                            new_indent = 0
                        insert_line = ' ' * new_indent + ins.content
                    raw_after.insert(i, insert_line + '\n')
                    i += 1
            if not ok:
                continue
            raw_lines = raw_before + raw_after
            # 重新构建 lines 对象列表（供后续块使用）
            lines = self._normalize_lines(raw_lines)
            success = True

        if success:
            # 写回文件（注意 raw_lines 已经是字符串列表，但每行可能没有换行符？我们在上面插入时已经加了换行）
            # 确保每行都有换行符
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(raw_lines)
        return success

class EchoHandler(ActionHandler):
    """处理 ECHO 消息。"""
    def handle(self, message: str, _: Optional[str] = None) -> None:
        if self.options.no_echo:
            return
        self.printer.echo(message)

# ===================== DiffBlock 数据结构 =====================
class DiffBlock:
    """表示一个 MODIFY 块，包含上下文行和操作列表。"""
    def __init__(self, context: List[str], ops: List[Tuple[str, str]]):
        self.context = context
        self.ops = ops

# ===================== Markdown 解析器 =====================
class MarkdownProcessor:
    """解析 Markdown，按顺序执行操作。"""
    def __init__(self, printer: Printer, options: Options):
        self.printer = printer
        self.options = options
        self.handlers = {
            'create': CreateHandler(printer, options),
            'exec': ExecHandler(printer, options),
            'modify': ModifyHandler(printer, options),
            'echo': EchoHandler(printer, options)
        }

    def process(self, lines: List[str]) -> None:
        i = 0
        n = len(lines)
        in_code_block = False
        code_type = None
        code_lines = []
        target_path = None

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if not in_code_block:
                if stripped.startswith('!!!'):
                    msg = stripped[3:].lstrip()
                    self.handlers['echo'].handle(msg, None)
                    i += 1
                    continue

                if stripped.startswith('```'):
                    parts = stripped[3:].split(maxsplit=1)
                    rest = parts[1] if len(parts) > 1 else ''
                    if rest.startswith('CREATE:'):
                        code_type = 'create'
                        target_path = rest[len('CREATE:'):].strip()
                        code_lines = []
                        in_code_block = True
                    elif rest.startswith('MODIFY:'):
                        code_type = 'modify'
                        target_path = rest[len('MODIFY:'):].strip()
                        code_lines = []
                        in_code_block = True
                    elif rest.strip() == 'EXEC':
                        code_type = 'exec'
                        code_lines = []
                        in_code_block = True
                    else:
                        i += 1
                        continue
                    i += 1
                    continue
                i += 1
            else:
                if stripped.startswith('```'):
                    content = '\n'.join(code_lines)
                    if code_type in self.handlers:
                        self.handlers[code_type].handle(target_path, content)
                    in_code_block = False
                    code_type = None
                    target_path = None
                    code_lines = []
                    i += 1
                    continue
                else:
                    code_lines.append(line.rstrip('\n'))
                    i += 1

# ===================== 命令行参数解析 =====================
def parse_arguments() -> Options:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', help='输入的 Markdown 文件（若不指定则从标准输入读取）')
    parser.add_argument('-c', '--auto-run', action='store_true', help='命令不用确认就运行')
    parser.add_argument('-o', '--skip-existing', action='store_true', help='跳过同名文件')
    parser.add_argument('-f', '--force', action='store_true', help='不确认直接覆盖')
    parser.add_argument('-n', '--no', action='store_true', help='全部拒绝')
    parser.add_argument('-y', '--yes', action='store_true', help='不确认直接覆盖和运行')
    parser.add_argument('-s', '--silent', action='store_true', help='静默运行，不提示动作')
    parser.add_argument('-w', '--no-echo', action='store_true', help='不显示 ECHO 消息')
    parser.add_argument('-r', '--no-run', action='store_true', help='不运行任何命令')
    parser.add_argument('-M', '--skip-modify', action='store_true', help='跳过所有 MODIFY 操作')
    parser.add_argument('-a', '--all-confirm', action='store_true', help='所有操作都必须经过确认')
    parser.add_argument('-L', '--leeway', type=int, default=3,
                        help='上下文匹配的最大允许跳过行数，-1无限制，0必须连续（默认3）')
    parser.add_argument('-d', '--fuzzy-indent', action='store_true', default=False,
                        help='开启模糊缩进匹配（默认关闭）')
    parser.add_argument('-D', '--strict-indent', action='store_false', dest='fuzzy_indent',
                        help='关闭模糊缩进匹配（默认）')
    args = parser.parse_args()
    # 默认 fuzzy_indent 为 False（即严格模式）
    if not hasattr(args, 'fuzzy_indent'):
        args.fuzzy_indent = False
    return Options(args)

# ===================== 主函数 =====================
def main() -> None:
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)

    options = parse_arguments()
    printer = Printer(options.silent)

    # 读取输入
    if options.file:
        try:
            with open(options.file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            sys.stderr.write(f"Error: File '{options.file}' not found.\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"Error reading file: {e}\n")
            sys.exit(1)
    else:
        lines = sys.stdin.readlines()

    processor = MarkdownProcessor(printer, options)
    processor.process(lines)

if __name__ == '__main__':
    main()