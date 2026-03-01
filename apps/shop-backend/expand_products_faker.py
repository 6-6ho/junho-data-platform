import psycopg2
import os
import random
from faker import Faker

# Configure Faker
fake = Faker()

# Database connection settings
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("POSTGRES_DB", "app")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "postgres")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def generate_products(n=10):
    products = []
    categories = ['Electronics', 'Clothing', 'Home', 'Books', 'Sports', 'Beauty', 'Toys']
    
    for _ in range(n):
        category = random.choice(categories)
        if category == 'Electronics':
            name = f"{fake.company()} {fake.word().capitalize()} {random.choice(['Pro', 'Max', 'Lite', 'Plus'])}"
        elif category == 'Clothing':
            name = f"{fake.color_name().capitalize()} {fake.word().capitalize()} {random.choice(['Shirt', 'Pants', 'Jacket', 'Shoes'])}"
        else:
            name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
            
        product = {
            'name': name,
            'category': category,
            'price': round(random.uniform(10.0, 500.0), 2),
            'description': fake.text(),
            'image_url': f"https://picsum.photos/seed/{fake.uuid4()}/200/300"
        }
        products.append(product)
    return products

def save_products(products):
    conn = get_db_connection()
    cur = conn.cursor()
    
    inserted_count = 0
    try:
        # Create table if not exists (idempotent)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shop_product (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                category VARCHAR(100),
                price DECIMAL(10, 2),
                description TEXT,
                image_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        for p in products:
            try:
                cur.execute("""
                    INSERT INTO shop_product (name, category, price, description, image_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING;
                """, (p['name'], p['category'], p['price'], p['description'], p['image_url']))
                
                if cur.rowcount > 0:
                    inserted_count += 1
            except Exception as e:
                print(f"Error inserting product {p['name']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"Successfully inserted {inserted_count} new products.")
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import sys
    n = 50
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            print("Invalid number provided, defaulting to 50.")
    
    print(f"Starting product expansion (Faker) for {n} items...")
    new_products = generate_products(n=n)
    save_products(new_products)
    print("Done.")
