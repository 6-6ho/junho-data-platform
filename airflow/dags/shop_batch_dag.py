from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'shop_daily_aggregation',
    default_args=default_args,
    description='Daily Shopping Data Aggregation',
    schedule_interval='0 1 * * *',  # Run at 1 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['shop', 'spark']
) as dag:

    # The spark-job-runner service has the spark-submit client and the updated code
    # We use docker exec to run the command inside the container from the airflow container?
    # No, Airflow and Spark are in the same network. 
    # But Airflow container doesn't have spark-submit installed.
    # We should use SparkSubmitOperator or SSHOperator or DockerOperator.
    # Given the setup, Airflow is running as a container.
    # The simplest way in this "Docker Compose" environment without proper K8s
    # is to install spark-submit in Airflow OR trigger it via API.
    
    # However, our Airflow Dockerfile (junho-data-platform/airflow) creates a custom image.
    # Does it have Java/Spark? Unlikely by default.
    
    # ALTERNATIVE: Use BashOperator to call a script that SSHs or 
    # simply assumes we mount the spark-submit binaries?
    
    # LET'S LOOK AT EXISTING DAGS.
    # The existing twitter_crypto_collect.py uses BashOperator.
    
    # For now, let's assume we can run spark-submit from the spark-master or spark-job-runner.
    # Since we can't easily cross-container exec from Airflow without docker socket.
    
    # STRATEGY: 
    # The 'airflow' container currently doesn't have spark. 
    # But we can perhaps modify the command to rely on a 'spark-submit' wrapper 
    # or install it.
    
    # Wait, in the 'junho-data-platform' setup, how was Spark triggered before?
    # It wasn't. There were only streaming jobs running via 'start.sh'.
    # Only 'twitter_crypto_collect' was an Airflow DAG.
    
    # Update: I will use a simple SSH or Curl approach if Spark Master exposes REST API.
    # Spark Standalone Master exposes a REST API for submission on port 6066.
    # We can use that!
    
    # spark-master:6066/v1/submissions/create
    
    # But wait, our 'spark-job-runner' container has the code.
    # The Spark Master doesn't necessarily have the python files mounted at the same path.
    # Actually, we mounted './spark:/app' in build time or volume?
    # junho-data-platform/docker-compose.yml check needed.
    # 'spark-master' builds from ./spark context. So it HAS the code at /app/jobs/...
    
    # So we can submit pointing to local file on Driver (which is Master in cluster mode? No)
    # in Client mode, the submitter needs the code.
    # in Cluster mode, the Driver runs on a Worker.
    
    # Let's try executing via curl to Spark Master REST API (Cluster Mode).
    # This requires the code to be available to the Driver (Worker).
    # Since all spark containers are built from same image, they all have /app/jobs/shop/batch.py.
    
    submit_job = BashOperator(
        task_id='submit_daily_aggregation',
        bash_command="""
        curl -X POST http://spark-master:6066/v1/submissions/create \
        --header "Content-Type:application/json;charset=UTF-8" \
        --data '{
            "action": "CreateSubmissionRequest",
            "appArgs": [ "{{ ds }}" ],
            "appResource": "file:///app/jobs/shop/batch.py",
            "clientSparkVersion": "3.5.0",
            "environmentVariables": {
                "SPARK_ENV_LOADED": "1"
            },
            "mainClass": "org.apache.spark.deploy.PythonRunner",
            "sparkProperties": {
                "spark.master": "spark://spark-master:7077",
                "spark.submit.deployMode": "cluster",
                "spark.driver.supervise": "false",
                "spark.app.name": "ShopDailyAggregation",
                "spark.jars": "/app/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar,/app/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar,/app/jars/kafka-clients-3.4.1.jar,/app/jars/commons-pool2-2.11.1.jar,/app/jars/iceberg-spark-runtime-3.5_2.12-1.4.3.jar,/app/jars/hadoop-aws-3.3.4.jar,/app/jars/aws-java-sdk-bundle-1.12.262.jar"
            }
        }'
        """
    )
    # Note: Spark REST API for Python requires mainClass "org.apache.spark.deploy.PythonRunner"
    # and appResource pointing to the python file.
    # Dependencies (jars) need to be explicitly listed if they are not in default Classpath.
    # We know /app/jars has them.
    
