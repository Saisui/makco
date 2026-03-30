#!/usr/bin/env python3
"""
从 Markdown 中提取并执行 CREATE、EXEC、MODIFY 代码块和 ECHO 消息。
支持多种命令行参数控制交互行为，使用 RGB 颜色输出。
"""

import os
import sys
import argparse
import subprocess
from typing import List, Tuple, Optional

# ===================== 颜色函数 =====================
def fc(r: int, g: int, b: int) -> str:
  """返回 RGB 前景色 ANSI 转义码"""
  return f'\033[38;2;{r};{g};{b}m'

def bg(r: int, g: int, b: int) -> str:
  """返回 RGB 背景色 ANSI 转义码"""
  return f'\033[48;2;{r};{g};{b}m'

# 预定义颜色常量（便于使用）
COLOR_CREATE = bg(0, 128, 0) + fc(255, 255, 255)   # 绿底白字
COLOR_COVER  = bg(173, 255, 47) + fc(0, 0, 0)     # 黄绿底黑字
COLOR_EXEC   = bg(0, 100, 200) + fc(255, 255, 255) # 蓝底白字
COLOR_ECHO   = bg(0, 180, 180) + fc(255, 255, 255) # 浅蓝底白字
COLOR_WARN   = bg(255, 200, 0) + fc(0, 0, 0)       # 黄底黑字
COLOR_MODIFY = bg(128, 0, 128) + fc(255, 255, 255) # 紫底白字
COLOR_GRAY   = fc(128, 128, 128)                    # 灰色文本
COLOR_RESET  = '\033[0m'

# ===================== 全局选项 =====================
options: argparse.Namespace = None

# ===================== 辅助函数 =====================
def print_colored(prefix: str, prefix_color: str, text: str, text_color: str = COLOR_GRAY, end: str = '\n') -> None:
  """打印带颜色的前缀和文本，中间有一个无背景的空格。"""
  if not options.silent:
    sys.stdout.write(prefix_color + prefix + COLOR_RESET)
    sys.stdout.write(' ')
    sys.stdout.write(text_color + text + COLOR_RESET)
    sys.stdout.write(end)
    sys.stdout.flush()

def print_warn(message: str) -> None:
  """打印 WARN 消息。"""
  if not options.silent:
    sys.stdout.write(COLOR_WARN + ' WARN ' + COLOR_RESET)
    sys.stdout.write(' ')
    sys.stdout.write(COLOR_GRAY + message + COLOR_RESET + '\n')
    sys.stdout.flush()

def ask_yes_no(prompt: str = "", no_prompt: bool = False) -> bool:
  """
  询问用户 y/n，返回 True/False。
  若 no_prompt=True，则不显示 prompt，直接读取输入。
  支持全局自动确认/拒绝。
  """
  if options.silent:
    return True
  if options.auto_yes:
    return True
  if options.auto_no:
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

# ===================== MODIFY 核心函数 =====================
def modify(orig: str, diff: str) -> Tuple[str, bool]:
    """
    将 diff 格式的修改应用到源文本 orig，返回 (修改后的文本, 是否至少应用了一个块)。
    内部使用 print_warn 输出错误信息。
    """
    # 解析 diff 文本为块列表，每个块是行列表（原始行，带有前缀）
    def parse_diff_blocks(diff_text: str):
        lines = diff_text.splitlines()
        blocks = []
        current_block = []
        in_block = False

        for raw_line in lines:
            line = raw_line.rstrip('\n')
            if not line:
                continue
            first_char = line[0]

            # 分隔符：连续两个以上相同的 '=' 或 '@'
            if first_char in ('=', '@') and len(line) >= 2 and all(c == first_char for c in line):
                if in_block:
                    blocks.append(current_block)
                    current_block = []
                    in_block = False
                continue

            # 注释行
            if first_char == '#':
                continue

            # 其他行：上下文或操作行
            if not in_block:
                in_block = True
            current_block.append(line)

        if in_block:
            blocks.append(current_block)

        return blocks

    # 应用单个块到文件行列表，返回 (新的文件行列表, 是否成功)
    def apply_block(lines, block):
        pos = 0
        new_lines = lines[:]   # 复制一份
        for raw_line in block:
            first_char = raw_line[0]
            content = raw_line[1:]

            if first_char in ('-', '+'):
                # 操作行
                if first_char == '-':
                    # 检查当前行是否匹配
                    if pos < len(new_lines) and new_lines[pos] == content:
                        del new_lines[pos]
                        # pos 不变，因为下一行上移
                    else:
                        print_warn(f"expected line '{content}' not found at position {pos}")
                        return lines, False
                else:  # '+'
                    new_lines.insert(pos, content)
                    pos += 1
            else:
                # 上下文行
                # 如果上下文行是空白行（仅空白），则跳过（不消耗位置）
                if not content.strip():
                    continue
                if pos >= len(new_lines):
                    print_warn(f"context line '{content}' not found at end of file")
                    return lines, False
                if content.strip() not in new_lines[pos].strip():
                    print_warn(f"context line '{content}' not matched at line {pos}: '{new_lines[pos]}'")
                    return lines, False
                pos += 1
        return new_lines, True

    orig_lines = orig.splitlines()
    blocks = parse_diff_blocks(diff)
    any_success = False
    for block in blocks:
        new_lines, success = apply_block(orig_lines, block)
        if success:
            orig_lines = new_lines
            any_success = True
        else:
            print_warn("block failed, skipping")
    return '\n'.join(orig_lines), any_success

# ===================== 核心操作处理 =====================
def handle_create(filepath: str, content: str) -> None:
  """处理 CREATE 块：创建文件（自动创建目录），处理覆盖策略。"""
  dirname = os.path.dirname(filepath)
  if dirname:
    os.makedirs(dirname, exist_ok=True)

  force = options.force_overwrite
  skip = options.skip_existing

  # -a 模式：先询问
  if options.all_confirm:
    exists = os.path.exists(filepath)
    if exists:
      if not options.silent:
        sys.stdout.write(COLOR_WARN + ' WARN ' + COLOR_RESET)
        sys.stdout.write(' ')
        sys.stdout.write(COLOR_GRAY + filepath + COLOR_RESET)
        sys.stdout.write(' - Overwrite? (y/n) ')
        sys.stdout.flush()
    else:
      if not options.silent:
        sys.stdout.write(COLOR_CREATE + ' CREATE ' + COLOR_RESET)
        sys.stdout.write(' ')
        sys.stdout.write(COLOR_GRAY + filepath + COLOR_RESET)
        sys.stdout.write(' - Create? (y/n) ')
        sys.stdout.flush()
    if not ask_yes_no(no_prompt=True):
      if not options.silent:
        sys.stdout.write(COLOR_GRAY + " (skipped)" + COLOR_RESET + '\n')
      return
    # 同意后强制覆盖（忽略 skip）
    force = True
    skip = False

  if os.path.exists(filepath):
    if skip:
      if not options.silent:
        print_colored(' CREATE ', COLOR_CREATE, filepath, COLOR_GRAY)
        sys.stdout.write(COLOR_GRAY + " (skipped, file exists)" + COLOR_RESET + '\n')
      return
    if force:
      with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
      if not options.silent:
        print_colored(' COVER ', COLOR_COVER, filepath, COLOR_GRAY)
      return
    # 普通覆盖询问（非 -a 且未强制）
    if not options.silent:
      sys.stdout.write(COLOR_WARN + ' WARN ' + COLOR_RESET)
      sys.stdout.write(' ')
      sys.stdout.write(COLOR_GRAY + filepath + COLOR_RESET)
      sys.stdout.write(' - Overwrite? (y/n) ')
      sys.stdout.flush()
    if ask_yes_no(no_prompt=True):
      with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
      if not options.silent:
        print_colored(' COVER ', COLOR_COVER, filepath, COLOR_GRAY)
    else:
      if not options.silent:
        sys.stdout.write(COLOR_GRAY + " (skipped)" + COLOR_RESET + '\n')
  else:
    with open(filepath, 'w', encoding='utf-8') as f:
      f.write(content)
    if not options.silent:
      print_colored(' CREATE ', COLOR_CREATE, filepath, COLOR_GRAY)

def handle_exec(command_str: str) -> None:
  """处理 EXEC 块：执行 shell 命令。"""
  lines = command_str.splitlines()
  if len(lines) == 1:
    if not options.silent:
      sys.stdout.write(COLOR_EXEC + ' EXEC ' + COLOR_RESET)
      sys.stdout.write(' ')
      sys.stdout.write(COLOR_GRAY + command_str + COLOR_RESET + '\n')
  else:
    if not options.silent:
      sys.stdout.write(COLOR_EXEC + ' EXEC ' + COLOR_RESET + '\n')
      sys.stdout.write(COLOR_GRAY + command_str + COLOR_RESET + '\n')
  sys.stdout.flush()

  run = False
  if options.no_run:
    run = False
  elif options.all_confirm:
    run = ask_yes_no("Run this command?")
  elif options.auto_yes or options.auto_exec:
    run = True
  elif options.auto_no:
    run = False
  else:
    run = ask_yes_no("Run this command?")

  if run:
    try:
      subprocess.run(command_str, shell=True, check=False)
    except Exception as e:
      sys.stderr.write(f"Error executing command: {e}\n")
  else:
    if not options.silent:
      sys.stdout.write(COLOR_GRAY + " (skipped)" + COLOR_RESET + '\n')

def handle_modify(filepath: str, content: str) -> None:
  """处理 MODIFY 块：修改文件内容。"""
  if options.skip_modify:
    if not options.silent:
      print_colored(' MODIFY ', COLOR_MODIFY, filepath, COLOR_GRAY)
      sys.stdout.write(COLOR_GRAY + " (skipped by -M)" + COLOR_RESET + '\n')
    return

  # -a 模式询问
  if options.all_confirm:
    if not options.silent:
      sys.stdout.write(COLOR_MODIFY + ' MODIFY ' + COLOR_RESET)
      sys.stdout.write(' ')
      sys.stdout.write(COLOR_GRAY + filepath + COLOR_RESET)
      sys.stdout.write(' - Apply? (y/n) ')
      sys.stdout.flush()
    if not ask_yes_no(no_prompt=True):
      if not options.silent:
        sys.stdout.write(COLOR_GRAY + " (skipped)" + COLOR_RESET + '\n')
      return

  # 读取文件内容
  try:
    with open(filepath, 'r', encoding='utf-8') as f:
      orig = f.read()
  except FileNotFoundError:
    print_warn(f"{filepath} - file does not exist, skipping")
    return

  # 应用修改
  if not options.silent:
    print_colored(' MODIFY ', COLOR_MODIFY, filepath, COLOR_GRAY)

  new_content, success = modify(orig, content)

  if success:
    with open(filepath, 'w', encoding='utf-8') as f:
      f.write(new_content)
  else:
    if not options.silent:
      sys.stdout.write(COLOR_GRAY + " (modification failed)" + COLOR_RESET + '\n')

def handle_echo(message: str) -> None:
  """处理 ECHO 消息。"""
  if options.no_echo:
    return
  if not options.silent:
    print_colored(' ECHO ', COLOR_ECHO, message, COLOR_GRAY)

# ===================== Markdown 解析 =====================
def process_markdown(lines: List[str]) -> None:
  """解析输入行，顺序处理块和消息。"""
  i = 0
  n = len(lines)
  in_code_block = False
  code_type = None          # 'create', 'exec', 'modify'
  code_lines = []
  target_path = None

  while i < n:
    line = lines[i]
    stripped = line.strip()

    if not in_code_block:
      if stripped.startswith('!!!'):
        msg = stripped[3:].lstrip()
        handle_echo(msg)
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
        if code_type == 'create':
          handle_create(target_path, content)
        elif code_type == 'exec':
          handle_exec(content)
        elif code_type == 'modify':
          handle_modify(target_path, content)
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
def parse_args() -> argparse.Namespace:
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
  parser.add_argument('-a', '--all-confirm', action='store_true', help='所有操作（CREATE, COVER, EXEC, MODIFY）都必须经过确认')
  args = parser.parse_args()

  # 处理冲突
  auto_yes = args.yes
  auto_no = args.no
  if auto_yes and auto_no:
    auto_no = False

  # 创建选项对象并设置属性
  opts = argparse.Namespace()
  opts.file = args.file
  opts.auto_exec = args.auto_run
  opts.skip_existing = args.skip_existing
  opts.force_overwrite = args.force
  opts.auto_yes = auto_yes
  opts.auto_no = auto_no
  opts.silent = args.silent
  opts.no_echo = args.no_echo
  opts.no_run = args.no_run
  opts.skip_modify = args.skip_modify
  opts.all_confirm = args.all_confirm

  # 应用优先级
  if opts.auto_yes:
    opts.auto_exec = True
    opts.force_overwrite = True
    opts.skip_existing = False
  if opts.auto_no:
    opts.auto_exec = False
    opts.force_overwrite = False
    opts.skip_existing = True
  if opts.no_run:
    opts.auto_exec = False
  if opts.all_confirm:
    opts.auto_yes = False
    opts.auto_no = False
    opts.auto_exec = False
    opts.force_overwrite = False
    opts.skip_existing = False

  return opts

# ===================== 主函数 =====================
def main() -> None:
  global options
  if len(sys.argv) == 1:
    print(__doc__)
    sys.exit(0)

  options = parse_args()

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

  process_markdown(lines)

if __name__ == '__main__':
  main()