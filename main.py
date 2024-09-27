from argparse import ArgumentParser
from pathlib import Path
import re


preprocess_only = False
assemble_only = False
print_state = False
instruction_table = {
    "inc": 0,
    "jnzdec": 1,
    "print": 2,
    "halt": 3,
}


class Assembler:
    def __init__(self, source, memsize):
        self.lines = source.splitlines()
        self.memsize = memsize
        self.unique_counter = 0
        self.labels = {}
    
    def assemble(self):
        # 全処理
        self.process_include()
        self.strip_lines()
        self.process_macro()
        if macro_expansion_only:
            for line in self.lines:
                print(line)
            return []
        self.process_label()
        if print_label_table:
            for name, address in self.labels.items():
                print(f"{name}: {address}")
            return []
        if preprocess_only:
            for i, line in enumerate(self.lines):
                print(f"{i}: {line}")
            return []
        executable = self.generate_executable()
        if assemble_only:
            print(executable)
            return []
        return executable
    
    def strip_lines(self):
        # コメント、空白行、インデントを削除
        result = []
        for line in self.lines:
            # コメントとインデント削除
            cleaned_line = line.strip().split("#", 1)[0]
            # 空白行以外だけ残す
            if cleaned_line:
                result.append(cleaned_line)
        self.lines = result
    
    def process_include(self):
        # includeされているファイルを読み込み、include行をファイルの内容で置換
        lines_len = len(self.lines)
        for i, line in enumerate(self.lines[:]):
            if line.startswith(".include"):
                filename = line.split()[1]
                filepath = Path(filename).resolve()
                with open(filepath) as f:
                    included_content = f.read()
                    sub_asm = Assembler(included_content, 0)
                    sub_asm.process_include()
                    self.lines[i-lines_len:i+1-lines_len] = sub_asm.lines
    
    def process_macro(self):
        # マクロの展開と定義の削除を行う
        inside_macro = False
        macro_begin = 0
        macro_name = ""
        macro_args = []
        macro_lines = []
        for i, line in enumerate(self.lines):
            if line.startswith(".def"):
                # 定義開始の行
                inside_macro = True
                macro_begin = i
                words = line[4:].split()
                macro_name = words[0]
                macro_args = words[1:]
            elif inside_macro:
                if line == ".end":
                    # 定義終了の行
                    inside_macro = False
                    # 定義の行を削除
                    self.lines[macro_begin:i+1] = []
                    # マクロ展開
                    self.expand_macro(macro_name, macro_args, "\n".join(macro_lines))
                    # 他にまだマクロがあれば処理
                    self.process_macro()
                    return
                else:
                    # 定義の途中の行
                    macro_lines.append(line)
            else:
                # マクロ定義以外の行
                pass
    
    def expand_macro(self, name, args, content):
        # マクロを呼び出している行を探し、置換する
        lines_len = len(self.lines)
        for i, line in enumerate(self.lines[:]):
            words = line.split()
            if words[0] == name:
                expanded_content = content
                # マクロ内のラベル名にマクロ名とカウンターの値を追加してユニーク化
                for expanded_line in expanded_content.splitlines():
                    if expanded_line[-1] == ":":
                        label_name = expanded_line[:-1]
                        unique_label_name = f"{label_name}_{name}{self.unique_counter}"
                        expanded_content = expanded_content.replace(expanded_line, unique_label_name+":")
                        expanded_content = re.sub(rf"(?<!\w|_){label_name}(?!\w|_)", unique_label_name, expanded_content)
                self.unique_counter += 1
                # マクロの引数を実引数に置換
                actual_params = words[1:]
                for j, arg in enumerate(args):
                    expanded_content = re.sub(rf"(?<!\w|_){arg}(?!\w|_)", "{"+str(j)+"}", expanded_content)
                expanded_content = expanded_content.format(*actual_params)
                # マクロの呼び出し行を置換
                self.lines[i-lines_len:i+1-lines_len] = expanded_content.splitlines()
    
    def process_label(self):
        # ラベルをアドレスに展開して、ラベル定義を削除
        lines_len = len(self.lines)
        address = 0
        for i, line in enumerate(self.lines[:]):
            if line[-1] == ":":
                name = line[:-1]
                del self.lines[i-lines_len]
                self.labels[name] = address
                self.expand_label(name, address)
            else:
                address += 1
    
    def expand_label(self, name, address):
        # ラベル名をアドレスに置換
        self.lines = [re.sub(rf"(?<!\w){name}(?!\w)", str(address), line) for line in self.lines]
    
    def generate_executable(self):
        # 機械語を生成する
        result = []
        for line in self.lines:
            words = line.split()
            if words[0].isdecimal():
                # 数字のみの場合はデータとして扱う
                for word in words:
                    result.append(int(word))
            elif words[0] in ["halt"]:
                result.append(instruction_table[words[0]])
            elif words[0] in ["inc", "print"]:
                opcode = instruction_table[words[0]]
                index = int(words[1])
                result.append(opcode + index * len(instruction_table))
            elif words[0] in ["jnzdec"]:
                opcode = instruction_table[words[0]]
                index = int(words[1])
                counter = int(words[2])
                result.append(opcode + (index + counter * self.memsize) * len(instruction_table))
        return result


class CounterMachine:
    def __init__(self, program, memsize):
        # memsizeのメモリを確保して、最初の領域にprogramをコピー
        self.memsize = memsize
        self.memory = [0] * memsize
        self.memory[:len(program)] = program
        self.counter = 0

    def run(self):
        # programを実行する
        while self.counter < self.memsize:
            instruction = self.memory[self.counter]
            if print_state:
                print(f"Machine State: Counter: {self.counter}, Instruction: {instruction}")
            # 命令をデコード
            opcode = instruction % len(instruction_table)
            operand = instruction // len(instruction_table)
            if opcode == 0:
                self.inc(operand)
            elif opcode == 1:
                index = operand % self.memsize
                counter = operand // self.memsize
                self.jnzdec(index, counter)
            elif opcode == 2:
                self.print(operand)
            else:
                # haltの場合、終了する
                break
    
    def inc(self, index):
        # indexのアドレスの内容を1増やしてカウンタを進める
        self.memory[index] += 1
        self.counter += 1
    
    def jnzdec(self, index, counter):
        # indexのアドレスの内容が0ならカウンタを進める。内容が正の値なら1減らしてcounterへジャンプ
        if self.memory[index] == 0:
            self.counter += 1
        else:
            self.memory[index] -= 1
            self.counter = counter
    
    def print(self, index):
        # indexのアドレスの内容を表示
        print(f"Info: The value at address {index} is {self.memory[index]}")
        self.counter += 1


def main():
    parser = ArgumentParser()
    parser.add_argument("filename")
    parser.add_argument("--memsize", type=int, default=1024, help="カウントマシンのメモリサイズを指定できます")
    parser.add_argument("-s", "--state", action="store_true", help="実行時に現在のカウンタと命令の値を表示します")
    parser.add_argument("-m", "--macro", action="store_true", help="マクロ展開の結果を表示します")
    parser.add_argument("-l", "--label", action="store_true", help="ラベル名と対応するアドレスの一覧を表示します")
    parser.add_argument("-p", "--preprocess", action="store_true", help="ラベルをアドレスに展開した結果のコードを表示します")
    parser.add_argument("-a", "--assemble", action="store_true", help="機械語を生成して表示します")
    args = parser.parse_args()
    global print_state
    global macro_expansion_only
    global print_label_table
    global preprocess_only
    global assemble_only
    print_state = args.state
    macro_expansion_only = args.macro
    print_label_table = args.label
    preprocess_only = args.preprocess
    assemble_only = args.assemble
    with open(args.filename) as f:
        source = f.read()
        program = Assembler(source, args.memsize).assemble()
        if program:
            CounterMachine(program, args.memsize).run()


if __name__ == "__main__":
    main()
