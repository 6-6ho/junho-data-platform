FROM flink:1.18-java11

# Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-dev && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Download Kafka connector JAR
RUN mkdir -p /opt/flink/usrlib && \
    curl -fSL https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar \
    -o /opt/flink/usrlib/flink-sql-connector-kafka-3.1.0-1.18.jar && \
    curl -fSL https://repo1.maven.org/maven2/org/apache/flink/flink-json/1.18.1/flink-json-1.18.1.jar \
    -o /opt/flink/usrlib/flink-json-1.18.1.jar

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy application code
COPY common/ /opt/flink/usrlib/common/
COPY jobs/ /opt/flink/usrlib/jobs/

ENV PYTHONPATH=/opt/flink/usrlib

# Checkpoint directory with proper permissions
RUN mkdir -p /opt/flink/checkpoints && chmod 777 /opt/flink/checkpoints

WORKDIR /opt/flink
