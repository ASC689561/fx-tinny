export REDIS_URL=redis://:dsteam123@116.99.34.245:30503
export ZOOKEEPER_URL=116.99.34.245:30506
export CONFIG_PATH=/FS/config-remote
rq worker v39
# ssh reverse proxy
ssh -L 5000:mlflow.workspace.svc.cluster.local:80 -L 8888:proxy-public.workspace.svc.cluster.local:80 -L 8088:superset.workspace.svc.cluster.local:8088 -L 8000:mt5.fx.svc.cluster.local:8080 -L 8080:airflow-webserver.workspace.svc.cluster.local:8080 server
# note
* ở phần training có thể dùng sample được, không cần dùng dự đoán của agent, như thế thì egent ko cải thiện 
ở các ep test, nhưng ở trên thì vẫn tốt hơn. sẽ giúp chạy nhanh hơn
* đánh giá thử xs của agent,sl tp trên jupyter


# deploy fxapp
cat releases/1.60 | skaffold deploy -n fx -a -

# optuna create study
optuna create-study --study-name fx8 --storage "redis://:dsteam123@airflow-redis.workspace.svc.cluster.local:6379"

# export/import exp

export MLFLOW_S3_ENDPOINT_URL=http://minio.workspace.svc.cluster.local:9000  
export MLFLOW_TRACKING_URI=http://mlflow.workspace.svc.cluster.local:80  
export AWS_ACCESS_KEY_ID=minio  
export AWS_SECRET_ACCESS_KEY=dsteam123  
export AWS_DEFAULT_REGION=test  
export AWS_BUCKET_NAME=mlflow  
export-experiment --experiment 20220826-2 --output-dir 20220826-2   


# mlflow kubectl gc
POD=`kgp | grep mlflow | grep -v postgres | cut -d' ' -f1`
kubectl exec "$POD" -- /bin/sh -c 'MLFLOW_S3_ENDPOINT_URL=http://minio.workspace.svc.cluster.local:9000 \
MLFLOW_TRACKING_URI=http://mlflow.workspace.svc.cluster.local:80 \
AWS_ACCESS_KEY_ID=minio  \
AWS_SECRET_ACCESS_KEY=dsteam123  \
AWS_DEFAULT_REGION=test  \
AWS_BUCKET_NAME=mlflow  \
mlflow gc --backend-store-uri postgresql://postgres:postgres@mlflow-postgresql.workspace.svc.cluster.local:5432/mlflow'


# mlflow gc
export MLFLOW_S3_ENDPOINT_URL=http://minio.workspace.svc.cluster.local:9000  
export MLFLOW_TRACKING_URI=http://mlflow.workspace.svc.cluster.local:80  
export AWS_ACCESS_KEY_ID=minio  
export AWS_SECRET_ACCESS_KEY=dsteam123  
export AWS_DEFAULT_REGION=test  
export AWS_BUCKET_NAME=mlflow  
mlflow gc --backend-store-uri postgresql://postgres:postgres@mlflow-postgresql.workspace.svc.cluster.local:5432/mlflow



# create db table - automated by airflow

> CREATE TABLE IF NOT EXISTS fx_test_strategy (
>    key VARCHAR(100) NOT NULL,
>    exp_name VARCHAR(100) NOT NULL,
>    start_time VARCHAR(100) NOT NULL,
>    end_time VARCHAR(100) NOT NULL,
>    created_time TIMESTAMP NOT NULL,
>    len INT NOT NULL,
>    action_stats VARCHAR(100)NOT NULL,
>    ind INT NOT NULL ,
>    pos INT NOT NULL,
>    trade INT,
>    equity  FLOAT(9) NOT NULL, 
>    sharpe  FLOAT(9) NOT NULL,
>    gain_rate FLOAT(9) NOT NULL 
> );


>CREATE TABLE IF NOT EXISTS fx_test_trade (
>   key VARCHAR(100),
>   exp_name VARCHAR(100),
>   time TIMESTAMP NOT NULL,
>   end_time TIMESTAMP NOT NULL,
>   created_time TIMESTAMP NOT NULL,
>   first_price FLOAT(9) NOT NULL,
>   second_price FLOAT(9) NOT NULL,
>   profit FLOAT(9) NOT NULL,
>   equity FLOAT(9) NOT NULL,
>   signal INT NOT NULL,
>   comment VARCHAR(255) NOT NULL
>);

>CREATE TABLE IF NOT EXISTS fx_live_trade (
>key VARCHAR(100) NOT NULL,
>time TIMESTAMP NOT NULL,
>end_time TIMESTAMP NOT NULL,
>created_time TIMESTAMP NOT NULL,
>first_price FLOAT(9) NOT NULL,
>second_price FLOAT(9) NOT NULL,
>profit FLOAT(9) NOT NULL,
>equity FLOAT(9) NOT NULL,
>signal INT NOT NULL,
>comment VARCHAR(100) NOT NULL 
>);

# backup db
> kubectl -n workspace exec -it superset-postgresql-0 -- sh -c "PGPASSWORD=superset pg_dump -U superset superset > /tmp/backup_superset"
> kubectl -n workspace cp superset-postgresql-0:tmp/backup_superset ./backup/backup_superset


> kubectl -n workspace exec -it postgres-postgresql-0 -- sh -c "PGPASSWORD=postgres pg_dump -U postgres prices > /tmp/backup_prices"
> kubectl -n workspace cp postgres-postgresql-0:tmp/backup_prices ./backup/backup_prices

> kubectl -n workspace exec -it mlflow-postgresql-0 -- sh -c "PGPASSWORD=postgres pg_dump -U postgres mlflow > /tmp/backup_mlflow"
> kubectl -n workspace cp mlflow-postgresql-0:tmp/backup_mlflow ./backup/backup_mlflow


# expose nodeport

> k expose --type=NodePort svc minio --port 9000 --name minio-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":9000,"name":"api","protocol":"TCP","targetPort":9000,"nodePort":30501},{"port":9001,"name":"ui","protocol":"TCP","targetPort":9001,"nodePort":30502}]}}'


> k expose --type=NodePort svc mlflow --port 80 --name mlflow-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":80,"name":"api","protocol":"TCP","targetPort":80,"nodePort":30500}]}}'


> k expose --type=NodePort svc airflow-redis --port 6379 --name airflow-redis-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":6379, "protocol":"TCP","targetPort":6379,"nodePort":30503}]}}'

> k expose --type=NodePort svc postgres-postgresql --port 5432 --name postgres-postgresql-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":5432, "protocol":"TCP","targetPort":5432,"nodePort":30504}]}}'

> k expose -n fx --type=NodePort svc logstash-logstash --port 8080 --name logstash-logstash-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":8080, "protocol":"TCP","targetPort":8080,"nodePort":30505}]}}'

> k expose -n fx --type=NodePort svc zookeeper --port 2181 --name zookeeper-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":2181, "protocol":"TCP","targetPort":2181,"nodePort":30506}]}}'

> k expose --type=NodePort svc proxy-public --port 80 --name proxy-public-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":80, "protocol":"TCP","targetPort":8000,"nodePort":30888}]}}'

> k expose -n fx --type=NodePort svc dashboard --port 8501 --name dashboard-nodeport  --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":8501, "protocol":"TCP","targetPort":8501,"nodePort":30507}]}}'

