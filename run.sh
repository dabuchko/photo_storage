#!/bin/bash

# compiling Vue project
cd frontend
npm run build
cd ..

# Starting nginx server for the Vue project
nginx -p ./ -c nginx.conf

# Starting API according to the configuration
source backend_config.cfg
python3 backend/main.py --host=$host --port=$port --path=$path $( [ "$https" = true ] && echo "--https" ) \
                        $( [ "$debug" = true ] && echo "--debug" ) --database_path=$database_path \
                        --secret_key=$secret_key --token_exp=$token_expiration --model_path=$model_path \
                        --album_matching_threshold=$album_matching_threshold --pred_batch_size=$pred_batch_size