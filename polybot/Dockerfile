FROM python:3.10-alpine
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
RUN apk update && apk add curl

ENV BUCKET_NAME="ehaborabi-bucket"
ENV TELEGRAM_APP_URL="https://ehabo-polybot-k8s-v1.int-devops.click"
ENV SQS_QUEUE_URL="https://sqs.eu-west-3.amazonaws.com/019273956931/ehabo-PolybotServiceQueue-k8s"
ENV SQS_QUEUE_NAME="ehabo-PolybotServiceQueue-k8s"
ENV REGION_NAME="eu-west-3" 
COPY . .

CMD ["python3", "app.py"]
