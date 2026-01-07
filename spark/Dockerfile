FROM python:3.11-slim

# Install Java (required for Spark)
RUN apt-get update && \
    apt-get install -y default-jre-headless && \
    apt-get clean;

ARG POETRY_VERSION=1.7.1
RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Download Spark-Kafka Jars
RUN mkdir -p /app/jars && \
    apt-get install -y wget && \
    wget -P /app/jars https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar && \
    wget -P /app/jars https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar && \
    wget -P /app/jars https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar && \
    wget -P /app/jars https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

COPY . .

# Keep container running for now
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
