import psycopg2
import os
import random
import json

# DB Connection
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "postgres"),
    port=os.getenv("DB_PORT", "5432"),
    database=os.getenv("POSTGRES_DB", "app"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "postgres")
)
conn.autocommit = True
cur = conn.cursor()

def seed_affinity():
    print("Seeding Affinity Data...")
    rules = [
        (["Laptop"], ["Wireless Mouse"], 0.85, 3.2, 0.05),
        (["Camera"], ["Lens", "Tripod"], 0.72, 2.8, 0.03),
        (["Running Shoes"], ["Socks"], 0.65, 2.1, 0.08),
        (["Smartphone"], ["Case", "Charger"], 0.78, 2.5, 0.12),
        (["Coffee Machine"], ["Coffee Beans"], 0.92, 4.5, 0.04),
        (["Gaming Console"], ["Controller"], 0.88, 3.8, 0.06),
        (["Tablet"], ["Stylus"], 0.55, 1.8, 0.07),
        (["Monitor"], ["HDMI Cable"], 0.60, 2.2, 0.09)
    ]
    
    cur.execute("TRUNCATE TABLE mart_product_association")
    
    for ant, con, conf, lift, supp in rules:
        cur.execute("""
            INSERT INTO mart_product_association (antecedents, consequents, confidence, lift, support)
            VALUES (%s, %s, %s, %s, %s)
        """, (str(ant), str(con), conf, lift, supp))

def seed_rfm():
    print("Seeding RFM Data...")
    segments = ["VIP", "Loyal", "Potential", "Risk", "Hibernating"]
    
    cur.execute("TRUNCATE TABLE mart_user_rfm")
    
    # Generate 100 dummy users
    for i in range(100):
        user_id = f"user_{i}"
        segment = random.choice(segments)
        # Fake scores based on segment for realism
        if segment == "VIP":
            r, f, m = 5, 5, 5
        elif segment == "Risk":
            r, f, m = 1, 2, 2
        else:
            r, f, m = random.randint(2,4), random.randint(2,4), random.randint(2,4)
            
        cur.execute("""
            INSERT INTO mart_user_rfm (user_id, recency, frequency, monetary, r_score, f_score, m_score, rfm_segment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, random.randint(1, 30), random.randint(1, 20), random.randint(100, 10000), r, f, m, segment))

try:
    seed_affinity()
    seed_rfm()
    print("Seeding Completed Successfully.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
