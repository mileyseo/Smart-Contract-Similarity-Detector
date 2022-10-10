from config import *
# from typing import Dict
import json
import os, re
from pathlib import Path
from typing import Optional
import solcx
from random import sample
import gensim
from gensim.models.doc2vec import TaggedLineDocument
from gensim.models.doc2vec import TaggedDocument
import torch
import random
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
import pandas as pd
from tqdm import tqdm
import subprocess
import csv

VOID_START = re.compile('//|/\*|"|\'')
PRAGMA = re.compile('pragma solidity.*?;')
QUOTE_END = re.compile("(?<!\\\\)'")
DQUOTE_END = re.compile('(?<!\\\\)"')

ORIG_DIR = './etherscan/'
COMPILED_DIR = 'compile_output'
COMPILED_DIR_OPT = 'compile_output_opt'
LOG_DIR = 'log'
DATA_DIR = 'dataset'
MODEL_WEIGHT = 'model_weight'
if not os.path.isdir(MODEL_WEIGHT):
    os.mkdir(MODEL_WEIGHT)
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)

OPCODE_SET = {"STOP", "ADD", "MUL", "SUB", "DIV", "SDIV", "MOD", "SMOD", "ADDMOD", "MULMOD", "EXP", "SIGNEXTEND", "LT",
              "GT", "SLT", "SGT", "EQ", "ISZERO", "AND", "OR", "EVMOR", "XOR", "NOT", "BYTE", "SHL", "SHR", "SAR",
              "SHA3", "ADDRESS", "BALANCE", "ORIGIN", "CALLER", "CALLVALUE", "CALLDATALOAD", "CALLDATASIZE",
              "CALLDATACOPY", "CODESIZE", "CODECOPY", "GASPRICE", "EXTCODESIZE", "EXTCODECOPY", "RETURNDATASIZE",
              "RETURNDATACOPY", "EXTCODEHASH", "BLOCKHASH", "COINBASE", "TIMESTAMP", "NUMBER", "DIFFICULTY", "GASLIMIT",
              "POP", "MLOAD", "MSTORE", "MSTORE8", "SLOAD", "SSTORE", "JUMP", "JUMPI", "PC", "MSIZE", "GAS", "JUMPDEST",
              "PUSH1", "PUSH2", "PUSH3", "PUSH4", "PUSH5", "PUSH6", "PUSH7", "PUSH8", "PUSH9", "PUSH10", "PUSH11",
              "PUSH12", "PUSH13", "PUSH14", "PUSH15", "PUSH16", "PUSH17", "PUSH18", "PUSH19", "PUSH20", "PUSH21",
              "PUSH22", "PUSH23", "PUSH24", "PUSH25", "PUSH26", "PUSH27", "PUSH28", "PUSH29", "PUSH30", "PUSH31",
              "PUSH32", "DUP1", "DUP2", "DUP3", "DUP4", "DUP5", "DUP6", "DUP7", "DUP8", "DUP9", "DUP10", "DUP11",
              "DUP12", "DUP13", "DUP14", "DUP15", "DUP16", "SWAP1", "SWAP2", "SWAP3", "SWAP4", "SWAP5", "SWAP6",
              "SWAP7", "SWAP8", "SWAP9", "SWAP10", "SWAP11", "SWAP12", "SWAP13", "SWAP14", "SWAP15", "SWAP16", "LOG0",
              "LOG1", "LOG2", "LOG3", "LOG4", "CREATE", "CALL", "CALLCODE", "RETURN", "DELEGATECALL", "CREATE2",
              "STATICCALL", "REVERT", "INVALID", "SELFDESTRUCT", "SUICIDE", "SELFBALANCE"}


class SmartContract:
    '''
    This class represents a smart contract
    '''

    def __init__(self, file_name, config: Dict):
        # decide the type of file_name

        # config['save_path']
        pass

    def log_message(self):
        pass

    def convert_binary_opcode(self):
        pass

    def remove_void(line):
        while m := VOID_START.search(line):
            if m[0] == '//':
                return (line[:m.start()], False)
            if m[0] == '/*':
                end = line.find('*/', m.end())
                if end == -1:
                    return (line[:m.start()], True)
                else:
                    line = line[:m.start()] + line[end + 2:]
                    continue
            if m[0] == '"':
                m2 = DQUOTE_END.search(line[m.end():])
            else:  # m[0] == "'":
                m2 = QUOTE_END.search(line[m.end():])
            if m2:
                line = line[:m.start()] + line[m.end() + m2.end():]
                continue
            # we should not arrive here for a correct Solidity program
            return line[:m.start()], False
        return line, False

    def get_pragma(file: str) -> Optional[str]:
        in_comment = False
        for line in file.splitlines():
            if in_comment:
                end = line.find('*/')
                if end == -1:
                    continue
                else:
                    line = line[end + 2:]
            line, in_comment = remove_void(line)
            if m := PRAGMA.search(line):
                return m[0]
        return None

    def get_solc(filename: str) -> Optional[Path]:
        with open(filename) as f:
            file = f.read()
        try:
            pragma = get_pragma(file)
            pragma = re.sub(r">=0\.", r"^0.", pragma)
            version = solcx.install_solc_pragma(pragma)
            return solcx.get_executable(version)
        except:
            return None

    from solcx.install import get_executable
    from solcx.install import install_solc_pragma

    if not os.path.isdir(COMPILED_DIR):
        os.mkdir(COMPILED_DIR)

    if not os.path.isdir(COMPILED_DIR_OPT):
        os.mkdir(COMPILED_DIR_OPT)

    if not os.path.isdir(LOG_DIR):
        os.mkdir(LOG_DIR)

    def get_solc(filename: str) -> Optional[Path]:
        with open(filename) as f:
            file = f.read()
        try:
            pragma = get_pragma(file)
            pragma = re.sub(r">=0\.", r"^0.", pragma)
            version = install_solc_pragma(pragma)
            return get_executable(version)
        except:
            return None

    def convert_binary_opcode(is_optimized: bool):
        # TODO two version: --optimize or not --optimize and store in different directory
        # TODO record error message in log directory.
        # TODO reformat opcode

        for project_name in os.listdir(ORIG_DIR):
            sub_dir = os.path.join(ORIG_DIR, project_name)
            if os.path.isfile(sub_dir):
                continue
            file_list = os.listdir(sub_dir)
            assert len(file_list) == 2
            source_file = os.path.join(sub_dir, project_name + '.sol')
            solc_compiler = get_solc(source_file)
            if is_optimized:
                save_dir = os.path.join(COMPILED_DIR_OPT, project_name)
                prefix = '--overwrite --opcodes --bin --bin-runtime --abi --asm-json --optimize'
            else:
                save_dir = os.path.join(COMPILED_DIR, project_name)
                prefix = '--overwrite --opcodes --bin --bin-runtime --abi --asm-json'
            if not os.path.isdir(save_dir):
                os.mkdir(save_dir)
            cmd = '%s %s -o %s %s' % (solc_compiler, prefix, save_dir, source_file)

            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()

            log_dir_success = os.path.join(LOG_DIR, project_name + "_out.csv")
            log_dir_error = os.path.join(LOG_DIR, project_name + "_err.csv")
            fields = ['input', 'output', 'error']
            if process.returncode == 0:
                row = [source_file, save_dir, 'NONE']
                filename = log_dir_success

            else:
                row = [source_file, save_dir, process.stderr.read()]
                filename = log_dir_error

            with open(filename, 'w') as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(fields)
                csvwriter.writerow(row)

            # format_opcode(save_dir)

    def convert_source_opcode(self):
        pass

    def convert_bin(self):
        proj_path = Dict["proj_path"]
        save_path = Dict["save_path"]
        bin_file = f'{proj_path}/{save_path}/{Dict["bin_file"]}'
        if os.path.isfile(bin_file) and os.access(bin_file, os.R_OK):
            os.system(f'rax2 -s < {bin_file} > {bin_file}.bin')
        else:
            print(f'{bin_file} not found')

    def format_opcode(self, dir_name):
        for opcode_filename in os.listdir(dir_name):
            if opcode_filename.endswith("opcode"):
                fullPath = os.path.join(dir_name, opcode_filename)
                f = open(fullPath, 'r')
                for line in f:
                    formatted_opcode = open(fullPath, 'w')
                    hasfirstline = False
                    for opcode in line.split():
                        if bool(hasfirstline):  # line 1 has been written
                            if opcode in OPCODE_SET:
                                formatted_opcode.write('\n' + opcode + ' ')
                            else:
                                formatted_opcode.write(opcode + ' ')
                        else:  # No line has been written yet
                            formatted_opcode.write(opcode + ' ')
                            hasfirstline = True

    def save_opcode(self):
        pass


class DataBase:
    def __init__(self, dir_name, config):
        # scan file in dir_name
        # SmartContract(file_name, config)
        pass


smc = SmartContract("./SolcExample/contract_out/Project.bin", Dict["bin_file"])
smc.convert_bin()
