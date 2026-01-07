#!/bin/bash
echo "Starting Spark Jobs..."

# Start Movers Job
echo "Starting Movers Job..."
python jobs/movers_job.py &

# Start Alerts Job
echo "Starting Alerts Job..."
python jobs/alerts_job.py &

# Wait for any process to exit
wait -n
  
# Exit with status of process that exited first
exit $?
