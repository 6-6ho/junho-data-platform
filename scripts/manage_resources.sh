#!/bin/bash
# scripts/manage_resources.sh
# Docker 서비스 자원 관리를 위한 스크립트

MODE=$1

if [ -z "$MODE" ]; then
    echo "Usage: ./manage_resources.sh [mode]"
    echo "Modes:"
    echo "  minimal   - Run only core services (Postgres, MinIO, Airflow, Monitoring)"
    echo "  streaming - Run streaming pipeline (Generator, Kafka, Spark Streaming)"
    echo "  all       - Run all services"
    echo "  stop      - Stop all services"
    exit 1
fi

case $MODE in
    "minimal")
        echo "SWITCHING TO MINIMAL MODE (Batch & Monitoring only)..."
        docker compose stop shop-generator shop-analytics ingest spark-worker-1 spark-job-runner kafka
        echo "Stopped: shop-generator, shop-analytics, ingest, spark-worker, spark-job-runner, kafka"
        ;;
    
    "streaming")
        echo "SWITCHING TO STREAMING MODE..."
        docker compose start kafka spark-worker-1 spark-job-runner shop-generator
        echo "Started: kafka, spark-worker, spark-job-runner, shop-generator"
        ;;
        
    "all")
        echo "STARTING ALL SERVICES..."
        docker compose start
        ;;
        
    "stop")
        echo "STOPPING ALL SERVICES..."
        docker compose stop
        ;;
        
    *)
        echo "Unknown mode: $MODE"
        exit 1
        ;;
esac

echo "Done."
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
