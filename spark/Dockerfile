FROM apache/spark:3.5.0

USER root

# Install Python & Pip & System Deps
RUN apt-get update && \
    apt-get install -y python3 python3-pip wget curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python Libs
RUN pip3 install kafka-python-ng psycopg2-binary==2.9.9

# Download Spark-Kafka & Iceberg Jars (Same as Shopping project)
WORKDIR /opt/spark/jars

# Kafka Connectors
RUN curl -O https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar && \
    curl -O https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar && \
    curl -O https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.0/kafka-clients-3.5.0.jar && \
    curl -O https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

# Postgres JDBC Driver
RUN curl -O https://repo1.maven.org/maven2/org/postgresql/postgresql/42.6.0/postgresql-42.6.0.jar

# Iceberg Spark Runtime
RUN curl -O https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar

# AWS SDK for S3 (MinIO)
RUN curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar && \
    curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar

WORKDIR /app
COPY . .

# Make shell scripts executable
RUN chmod +x /app/*.sh

# Grant permissions to spark user
RUN chown -R 185:185 /app

# Switch back to spark user for security (and compatibility with Spark images)
# But for now, sticking to root might be safer for file permissions in mapped volumes?
# apache/spark runs as 185 by default. Let's try to be correct.
USER 185

ENV PYTHONPATH=$PYTHONPATH:/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip:/app
ENV PATH=$PATH:/opt/spark/bin

CMD ["./start.sh"]
