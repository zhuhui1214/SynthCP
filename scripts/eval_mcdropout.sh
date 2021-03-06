GPUs=$1
eval_output_dir=$2
python tools/eval_mcdropout.py --name cityscapes --dataset_mode iouentropy \
                --phase test --n_fold 0 \
                --dataroot ./cityscapes \
                --image_src_dir ./$eval_output_dir/cityscapes/leftImg8bitResize/val \
                --image_rec_dir ./$eval_output_dir/cityscapes/leftImg8bitRec/val \
                --entropy_dir ./$eval_output_dir/metrics_trainccv_mcd \
                --conf_map_dir ./$eval_output_dir/cityscapes/gtFinePred_mcdropout/val \
                --with_conf_map \
                --iou_dir ./$eval_output_dir/metrics_val \
                --pred_dir ./$eval_output_dir/cityscapes/gtFinePredProb/val \
                --label_nc 19 --no_instance --serial_batches --no_flip \
                --vgg_norm \
                --gpu_ids $GPUs