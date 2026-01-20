import os
import time
import socket
import logging
from datetime import datetime

import boto3
import requests
from dotenv import load_dotenv

# 로컬 .env 또는 시스템 환경변수 로드
load_dotenv()

# --- Configuration ---
DOMAIN_NAME = "junho.in"
HOSTED_ZONE_ID = os.getenv("AWS_HOSTED_ZONE_ID")  # Route53 Hosted Zone ID
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ddns_update.log")
    ]
)
logger = logging.getLogger(__name__)

def get_public_ip():
    """외부 IP 확인 서비스들을 통해 현재 공인 IP를 가져옵니다."""
    services = [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]
    
    for url in services:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return resp.text.strip()
        except Exception as e:
            logger.warning(f"Failed to fetch IP from {url}: {e}")
            continue
    return None

def get_current_dns_ip(client):
    """Route53에 현재 설정된 IP를 확인합니다."""
    try:
        resp = client.list_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            StartRecordName=DOMAIN_NAME,
            StartRecordType='A',
            MaxItems=1
        )
        records = resp.get('ResourceRecordSets', [])
        if records and records[0]['Name'] == f"{DOMAIN_NAME}.":
            return records[0]['ResourceRecords'][0]['Value']
    except Exception as e:
        logger.error(f"Failed to fetch Route53 record: {e}")
    return None

def update_dns_record(client, ip):
    """Route53 A 레코드를 업데이트합니다."""
    try:
        client.change_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            ChangeBatch={
                'Comment': 'Auto update by trade-helper DDNS script',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': DOMAIN_NAME,
                            'Type': 'A',
                            'TTL': 300,
                            'ResourceRecords': [{'Value': ip}]
                        }
                    }
                ]
            }
        )
        logger.info(f"Successfully updated DNS record to {ip}")
        return True
    except Exception as e:
        logger.error(f"Failed to update DNS record: {e}")
        return False

def main():
    if not all([HOSTED_ZONE_ID, AWS_ACCESS_KEY, AWS_SECRET_KEY]):
        logger.error("Missing AWS credentials or Hosted IP in env vars.")
        return

    client = boto3.client(
        'route53',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    current_ip = get_public_ip()
    if not current_ip:
        logger.error("Could not determine public IP.")
        return

    dns_ip = get_current_dns_ip(client)
    logger.info(f"Current Public IP: {current_ip}, DNS IP: {dns_ip}")

    if current_ip != dns_ip:
        logger.info("IP Changed! Updating DNS...")
        update_dns_record(client, current_ip)
    else:
        logger.info("IP is up to date. No action needed.")

if __name__ == "__main__":
    main()
