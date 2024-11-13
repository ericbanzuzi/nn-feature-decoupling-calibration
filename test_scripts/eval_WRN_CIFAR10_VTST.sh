#!/bin/bash	

cd /home/ericbanzuzi/DD2412-Final-Project/
export PYTHONPATH=$PWD
echo "!!Evaluating model!!"
python3 src/experiments/01_eval_models.py \
    --save_file_name WRN_CIFAR10_VTST.txt \
    --model_name_file evaluate_wrn_cifar10_vtst.txt \
    --num_samples 10
echo "!!Evaluation done!!"