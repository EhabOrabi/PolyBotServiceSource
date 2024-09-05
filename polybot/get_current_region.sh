#!/bin/sh

# Fetch the token for IMDSv2
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")

# Fetch the availability zone using the token
AVAILABILITY_ZONE=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/meta-data/placement/availability-zone")

# Extract the region name by removing the last character from the availability zone
REGION=${AVAILABILITY_ZONE%?}

# Export the region as an environment variable
export REGION_NAME=$REGION

export BUCKET_NAME="ehaborabi-bucket-$REGION-tf"
export TELEGRAM_APP_URL="https://ehabo-polybot2-$REGION.int-devops.click"
export SQS_QUEUE_URL="https://sqs.$REGION_NAME.amazonaws.com/019273956931/ehabo-PolybotServiceQueue-.$REGION.-tf"
export SQS_QUEUE_NAME="ehabo-PolybotServiceQueue-.$REGION.-tf"