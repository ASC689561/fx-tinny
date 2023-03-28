FROM python:3.7-slim

RUN apt update && apt install -y git gcc

RUN pip install numpy pandas grpcio streamlit rq redis kazoo PyYaml mlflow streamlit_autorefresh  
RUN pip3 install flask pymongo matplotlib
RUN pip3 install --force-reinstall --no-deps bokeh==2.4.3 boto3 botocore s3transfer jmespath   
RUN pip3 install git+https://github.com/ASC689561/cow.git

WORKDIR /code
COPY ./dashboard/ /code

ENTRYPOINT streamlit run dashboard.py