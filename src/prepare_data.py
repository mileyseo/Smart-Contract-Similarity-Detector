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

import adjustText

VOID_START = re.compile('//|/\*|"|\'')
PRAGMA = re.compile('pragma solidity.*?;')
QUOTE_END = re.compile("(?<!\\\\)'")
DQUOTE_END = re.compile('(?<!\\\\)"')


COMPILED_DIR = 'compile_output'
DATA_DIR = 'dataset'
MODEL_WEIGHT = 'model_weight'
if not os.path.isdir(MODEL_WEIGHT):
    os.mkdir(MODEL_WEIGHT)
if not os.path.isdir(DATA_DIR):
    os.mkdir(DATA_DIR)

def remove_void(line):
    while m := VOID_START.search(line):
        if m[0] == '//':
            return (line[:m.start()], False)
        if m[0] == '/*':
            end = line.find('*/', m.end())
            if end == -1:
                return (line[:m.start()], True)
            else:
                line = line[:m.start()] + line[end+2:]
                continue
        if m[0] == '"':
            m2 = DQUOTE_END.search(line[m.end():])
        else: # m[0] == "'":
            m2 = QUOTE_END.search(line[m.end():])
        if m2:
            line = line[:m.start()] + line[m.end()+m2.end():]
            continue
        # we should not arrive here for a correct Solidity program
        return (line[:m.start()], False)
    return (line, False)

def get_pragma(file: str) -> Optional[str]:
    in_comment = False
    for line in file.splitlines():
        if in_comment:
            end = line.find('*/')
            if end == -1:
                continue
            else:
                line = line[end+2:]
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


def compile_source_project(is_optim):
    # TODO two version: --optimize or not --optimize and store in different directory
    # TODO record error message in log directory.
    # TODO reformat opcode
    ORIG_DIR = './etherscan/'
    for project_name in os.listdir(ORIG_DIR):
        sub_dir = os.path.join(ORIG_DIR, project_name)
        if os.path.isfile(sub_dir):
            continue
        file_list = os.listdir(sub_dir)
        assert len(file_list) == 2
        source_file = os.path.join(sub_dir, project_name + '.sol')
        save_dir = os.path.join(COMPILED_DIR, project_name)
        if not os.path.isdir(save_dir):
            os.mkdir(save_dir)
        solc_compiler = get_solc(source_file)
        prefix = '--overwrite --opcodes --bin --bin-runtime --abi --asm-json'
        cmd = '%s %s -o %s %s' % (solc_compiler, prefix, save_dir, source_file)
        os.system(cmd)
