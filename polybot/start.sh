#!/bin/sh

# Source the get_current_region.sh script to set the environment variable
. /usr/src/app/get_current_region.sh

# Construct the SQS_QUEUE_URL dynamically
export SQS_QUEUE_URL="https://sqs.$REGION_NAME.amazonaws.com/019273956931/ehabo-PolybotServiceQueue-$REGION_NAME-tf"

export BUCKET_NAME="ehaborabi-bucket-$REGION-tf"
export TELEGRAM_APP_URL="https://ehabo-polybot2-$REGION.int-devops.click"
export SQS_QUEUE_NAME="ehabo-PolybotServiceQueue-$REGION-tf"

# Print the region and SQS_QUEUE_URL to verify
echo "Using region: $REGION_NAME"
echo "SQS Queue URL: $SQS_QUEUE_URL"
echo "Bucket Name: $BUCKET_NAME"
echo "Telegram App Url: $TELEGRAM_APP_URL"


# Start the application
exec python3 app.py
