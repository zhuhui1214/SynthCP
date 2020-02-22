import os.path
import os.path as osp
import sys
from collections import deque
from tqdm import *

import click
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from PIL import Image
from util.util import tensor2im
from options.fcn_options import BaseOptions

from models.fcn8 import VGG16_FCN8s
import data
import json
import pdb

def to_tensor_raw(im):
    return torch.from_numpy(np.array(im, np.int64, copy=False))


def fmt_array(arr, fmt=','):
    strs = ['{:.3f}'.format(x) for x in arr]
    return fmt.join(strs)

def fast_hist(a, b, n):
    k = (a >= 0) & (a < n)
    return np.bincount(n * a[k].astype(int) + b[k], minlength=n**2).reshape(n, n)

def result_stats(hist):
    acc_overall = np.diag(hist).sum() / hist.sum() * 100
    acc_percls = np.diag(hist) / (hist.sum(1) + 1e-8) * 100
    iu = np.diag(hist) / (hist.sum(1) + hist.sum(0) - np.diag(hist) + 1e-8) * 100
    freq = hist.sum(1) / hist.sum()
    fwIU = (freq[freq > 0] * iu[freq > 0]).sum()
    pix_percls = hist.sum(1)
    return acc_overall, acc_percls, iu, fwIU, pix_percls

ignore_label = 255
id2label = {-1: ignore_label, 0: ignore_label, 1: ignore_label, 2: ignore_label,
            3: ignore_label, 4: ignore_label, 5: ignore_label, 6: ignore_label,
            7: 0, 8: 1, 9: ignore_label, 10: ignore_label, 11: 2, 12: 3, 13: 4,
            14: ignore_label, 15: ignore_label, 16: ignore_label, 17: 5,
            18: ignore_label, 19: 6, 20: 7, 21: 8, 22: 9, 23: 10, 24: 11, 25: 12, 26: 13, 27: 14,
            28: 15, 29: ignore_label, 30: ignore_label, 31: 16, 32: 17, 33: 18}

#id2label_gta2cs = {}
#for k,v in id2label:
#    if v != ignore_label:
#        id2label_gta2cs[v] = k

# parse options
opt = BaseOptions().parse()
# print options to help debugging
print(' '.join(sys.argv))

# load the dataset
dataloader = data.create_dataloader(opt)

net = VGG16_FCN8s(num_cls=opt.label_nc, pretrained=False)
net.load_state_dict(torch.load(opt.model_path, map_location='cuda:{}'.format(opt.gpu_ids[0])))
net.cuda()
net.eval()
net.set_dropout_train_mode()

hist = np.zeros((19, 19))
metrics = []
samples = 50
iterations = tqdm(enumerate(dataloader), total=len(dataloader))
for i, data_i in iterations:
    # Clear out gradients

    # forward pass and compute loss
    im = data_i['image_seg'].cuda()
    label = data_i['label'].squeeze(1)
    #preds = net(im)

    outputs = torch.zeros(
                    samples,
                    im.shape[0],
                    opt.label_nc,
                    im.shape[2],
                    im.shape[3],
                ).cuda()
    with torch.no_grad():
        for j in range(samples):
            outputs[j] = net(im)
    score = outputs.mean(0)
    probs = F.softmax(score, dim=1).cpu()
    # entropy map
    confidence_map = (probs * torch.log(probs + 1e-9)).sum(dim=1)  # entropy
    # 1 vs all entropy
    confidence = torch.zeros_like(probs) #.cuda()
    for j in range(opt.label_nc):
        confidence[:,j,:,:] = probs[:,j,:,:] * torch.log(probs[:,j,:,:]+1e-9) + \
                        probs[:,torch.arange(opt.label_nc)!=j,:,:].sum(dim=1) * \
            torch.log(probs[:,torch.arange(opt.label_nc)!=j,:,:].sum(dim=1)+1e-9)
        #confidence[:,j,:,:] = (probs * torch.log(probs + 1e-9)).sum(dim=1)
    confidence = confidence.mean(dim=(2,3))
    #pdb.set_trace()
    #score = net(im).data
    #prob = score.cpu().numpy()[0]
    _, preds = torch.max(score, 1)


    hist = fast_hist(label.numpy().flatten(),
            preds.cpu().numpy().flatten(),
            19)
    acc_overall, acc_percls, iu, fwIU, pix_percls = result_stats(hist)
    iterations.set_postfix({'mIoU':' {:0.2f}  fwIoU: {:0.2f} pixel acc: {:0.2f} per cls acc: {:0.2f}'.format(
        np.nanmean(iu), fwIU, acc_overall, np.nanmean(acc_percls))})
    metric = [iu.tolist(), pix_percls.tolist(), fwIU, acc_overall, acc_percls.tolist(), confidence[0].numpy().tolist()]
    metrics.append(metric)
    if opt.phase == 'train':
        output_dir = osp.join(opt.eval_output_dir, 'metrics_trainccv_mcd')
    else:
        output_dir = osp.join(opt.eval_output_dir, 'metrics_mcd_val')
        conf_path = osp.join(opt.eval_output_dir, data_i['label_path'][0].replace('gtFine', 'gtFinePred_mcdropout'))
        os.makedirs(os.path.dirname(conf_path), exist_ok=True)
        np.savez_compressed(conf_path, confidence_map=confidence_map.cpu().numpy()[0])
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, os.path.splitext(os.path.basename(data_i['path'][0]))[0] + '.json'), 'w') as f:
        json.dump(metric, f)
print()
