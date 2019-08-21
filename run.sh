#python train.py --name GTA5_generator --dataset_mode cityscapes --label_dir ./datasets/GTA5/train_label -- image_dir ./datasets/GTA5/train_img
#python train.py --name GTA5_generator --dataset_mode custom --label_dir /data/gta5/labels --image_dir /data/gta5/images --no_instance --batchSize 32 --gpu_ids 0,1,2,3
python train.py --name GTA5_encode_image --dataset_mode custom \
                --label_dir /data/gta5/labels \
                --image_dir /data/gta5/images \
                --label_nc 35 --no_instance \
                --use_vae \
                --batchSize 12 \
                --gpu_ids 2