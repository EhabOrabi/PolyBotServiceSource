FROM python:3.10-alpine
WORKDIR /usr/src/app
# Copy requirements file
COPY requirements.txt .
# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
# Install curl using apk
RUN apk update && apk add curl
# Copy the rest of the application files
COPY . .
# Ensure get_current_region.sh is executable
RUN chmod +x /usr/src/app/get_current_region.sh
# Ensure start.sh is executable
RUN chmod +x /usr/src/app/start.sh
# Set default environment variables

# Run the start script
CMD ["/usr/src/app/start.sh"]
