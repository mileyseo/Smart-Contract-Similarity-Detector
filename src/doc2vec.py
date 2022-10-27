import os
import random
import torch
import gensim
from gensim.models.doc2vec import TaggedLineDocument
from gensim.models.doc2vec import TaggedDocument
import numpy as np


def preprocess(inst_path, data_dir):
    f = open(os.path.join(data_dir, inst_path), 'r')
    inst = f.readlines()
    f.close()
    return inst


def load_func(inst_path, data_dir):
    instructions = preprocess(inst_path, data_dir)
    sentences = TaggedDocument(instructions, [0])
    return sentences


def load_data(data_dir):
    instructions = [preprocess(d, data_dir) for d in os.listdir(data_dir)]
    sentences = [TaggedDocument(l, [i]) for i, l in enumerate(instructions)]
    random.shuffle(sentences)
    return sentences


def train_model(config: dict):
    sentences = []
    op_dir = config['REPO_PROJ_DIR']
    for proj in os.listdir(op_dir):
        sentences += load_data(os.path.join(op_dir, proj))
    # dm = 1 means ‘distributed memory’ (PV-DM)
    # dm = 0 means ‘distributed bag of words’ (PV-DBOW)
    model = gensim.models.doc2vec.Doc2Vec(dm=0)
    model.build_vocab(sentences)
    model.train(sentences, total_examples=model.corpus_count, epochs=10)

    if not os.path.isdir(config['MODEL_DIR']):
        os.mkdir(config['MODEL_DIR'])
    torch.save(model, config['MODEL_DIR'] + 'doc2vec.pt')


def compare_sim(config: dict):
    model = torch.load(config['MODEL_DIR'] + 'doc2vec.pt')
    target_dir = config['TARGET_PROJ_DIR']
    repo_dir = config['REPO_PROJ_DIR']
    for target in os.listdir(target_dir):
        for source in os.listdir(repo_dir):
            compare_proj_sim(os.path.join(target_dir, target), os.path.join(repo_dir, source), model)


def compare_proj_sim(target, source, model):
    print('=========================================')
    total_func_sim = 0
    tp = target.rsplit('/', 1)[-1]
    rp = source.rsplit('/', 1)[-1]
    print('target project: ', tp)
    print('repo project: ', rp)
    for tf in os.listdir(target):
        target_func = load_func(tf, target)
        tf_vec = model.infer_vector(target_func[0])
        max_func_sim = 0
        for rf in os.listdir(source):
            repo_func = load_func(rf, source)
            rp_vec = model.infer_vector(repo_func[0])
            sim = cosine_similarity(tf_vec, rp_vec)
            max_func_sim = max(max_func_sim, sim)
            print('sim("{}", "{}") = {}'.format(tf, rf, sim))
        total_func_sim += max_func_sim
    print('sim("{}", "{}") = {}'.format(tp, rp, total_func_sim / len(os.listdir(target))))
    print('=========================================')


def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))