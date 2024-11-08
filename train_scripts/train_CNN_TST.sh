cd /home/kathideckenbach/DD2412-Final-Project/
export PYTHONPATH=$PWD
echo "!!Training model!!"
python3 src/experiments/00_train_models.py \
    --model TST_CNN \
    --epochs 40 \
    --accelerator gpu \
    --seed 0 \
    --dataset CIFAR10 \
    --model_name CIFAR10_CNN_Base_TST \
    --batch_size 256 \
    --pretrained_qyx ../experiment_results/CIFAR10_CNN/checkpoints/seed=1-epoch=03-valid_loss=1.770-model_name=CIFAR10_CNN_Base_seed1.ckpt \
    --seeds_per_job 10 \
    --latent_dim 128 \
    --freeze_qyz True
echo "!!Training done!!"