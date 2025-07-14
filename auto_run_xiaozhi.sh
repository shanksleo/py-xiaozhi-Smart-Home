#!/bin/bash

# 激活 Conda 环境
eval "$(/home/tianjiao/miniconda3/condabin/conda shell.bash hook)"
conda activate py-xiaozhi

# 导航到工作目录
cd /home/tianjiao/originXiaoZhi/py-xiaozhi-Smart-Home/ || exit

# 使用指定路径的 Python 解释器执行程序
/usr/bin/python3 main.py --mode cli --protocol websocket