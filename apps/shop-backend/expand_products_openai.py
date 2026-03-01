import os
import psycopg2
import json
import random

# Configuration
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_NAME = os.environ.get("POSTGRES_DB", "app")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "postgres")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

def create_table_if_not_exists(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS shop_product (
            product_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            category VARCHAR(100),
            price INTEGER,
            description TEXT,
            image_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    print("Table shop_product checked/created.")

def get_hardcoded_products():
    return [
        {"name": "Vintage Denim Jacket", "category": "Outerwear", "price": 89000, "description": "Classic vintage denim jacket with a relaxed fit. perfect for layering.", "image_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8ZGVuaW0lMjBqYWNrZXR8ZW58MHx8MHx8fDI%3D"},
        {"name": "Silk Floral Blouse", "category": "Tops", "price": 120000, "description": "Elegant silk blouse featuring a delicate floral pattern. Ideal for office or evening wear.", "image_url": "https://images.unsplash.com/photo-1604176354204-9268737828e4?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YmxvdXNlfGVufDB8fDB8fHwy"},
        {"name": "Leather Chelsea Boots", "category": "Shoes", "price": 150000, "description": "Premium leather Chelsea boots with durable sole. Stylish and comfortable.", "image_url": "https://images.unsplash.com/photo-1638247026263-2c12f3274213?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8Y2hlbHNlYSUyMGJvb3RzfGVufDB8fDB8fHwy"},
        {"name": "Wool Blend Coat", "category": "Outerwear", "price": 230000, "description": "Warm wool blend coat in a timeless camel color. A winter essential.", "image_url": "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8Y29hdHxlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "High-Waisted Wide Leg Trousers", "category": "Bottoms", "price": 75000, "description": "Chic high-waisted trousers with a wide leg cut. Flattering and modern.", "image_url": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dHJvdXNlcnN8ZW58MHx8MHx8fDI%3D"},
        {"name": "Casual Cotton T-Shirt", "category": "Tops", "price": 25000, "description": "Soft cotton t-shirt in various colors. A comfortable staple for everyday wear.", "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dCUyMHNoaXJ0fGVufDB8fDB8fHwy"},
        {"name": "Pleated Midi Skirt", "category": "Bottoms", "price": 58000, "description": "Feminine pleated midi skirt. Moves beautifully with every step.", "image_url": "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8c2tpcnR8ZW58MHx8MHx8fDI%3D"},
        {"name": "Classic White Sneakers", "category": "Shoes", "price": 89000, "description": "Versatile white sneakers that go with everything. Clean and minimal design.", "image_url": "https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OHx8c25lYWtlcnN8ZW58MHx8MHx8fDI%3D"},
        {"name": "Knitted Oversized Sweater", "category": "Tops", "price": 65000, "description": "Cozy oversized sweater in a chunky knit. Perfect for chilly days.", "image_url": "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8OXx8c3dlYXRlcnxlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "Slim Fit Chinos", "category": "Bottoms", "price": 49000, "description": "Tailored slim fit chinos. Smart casual style for any occasion.", "image_url": "https://images.unsplash.com/photo-1473966968600-fa801b869a1a?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8Y2hpbm9zfGVufDB8fDB8fHwy"},
        {"name": "Structured Blazer", "category": "Outerwear", "price": 110000, "description": "Sharp structured blazer. Instantly broadens shoulders and elevates any look.", "image_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8YmxhemVyfGVufDB8fDB8fHwy"},
        {"name": "Floral Summer Dress", "category": "Dresses", "price": 72000, "description": "Lightweight floral dress for summer days. Breathable and pretty.", "image_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8ZHJlc3N8ZW58MHx8MHx8fDI%3D"},
        {"name": "Denim Shorts", "category": "Bottoms", "price": 35000, "description": "Classic denim shorts with a raw hem. Essential for warm weather.", "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8c2hvcnRzfGVufDB8fDB8fHwy"},
        {"name": "Bomber Jacket", "category": "Outerwear", "price": 85000, "description": "Trendy bomber jacket with ribbed cuffs. Adds a cool edge to your outfit.", "image_url": "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8amFja2V0fGVufDB8fDB8fHwy"},
        {"name": "Striped Linen Shirt", "category": "Tops", "price": 55000, "description": "Breathable linen shirt with subtle stripes. Relaxed and sophisticated.", "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8c2hpcnR8ZW58MHx8MHx8fDI%3D"},
        {"name": "Athletic Leggings", "category": "Bottoms", "price": 42000, "description": "High-performance leggings for workouts or athleisure. Stretchy and supportive.", "image_url": "https://images.unsplash.com/photo-1506619216599-9d16d0903dfd?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8bGVnZ2luZ3N8ZW58MHx8MHx8fDI%3D"},
        {"name": "Leather Belt", "category": "Accessories", "price": 28000, "description": "Genuine leather belt with a classic buckle. Durable and stylish.", "image_url": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8YmVsdHxlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "Beanie Hat", "category": "Accessories", "price": 18000, "description": "Soft knit beanie to keep you warm. Available in multiple colors.", "image_url": "https://images.unsplash.com/photo-1576871337632-b9aef4c17ab9?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8YmVhbmllfGVufDB8fDB8fHwy"},
        {"name": "Canvas Tote Bag", "category": "Accessories", "price": 22000, "description": "Durable canvas tote bag. Spacious enough for all your essentials.", "image_url": "https://images.unsplash.com/photo-1597484662317-9bd7bdda2907?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8dG90ZSUyMGJhZ3xlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "Sunglasses", "category": "Accessories", "price": 35000, "description": "Stylish sunglasses with UV protection. complete your summer look.", "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8c3VuZ2xhc3Nlc3xlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "Puffer Jacket", "category": "Outerwear", "price": 130000, "description": "Insulated puffer jacket for extreme cold. Lightweight yet very warm.", "image_url": "https://images.unsplash.com/photo-1544022613-e87ca75a784a?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8cHVmZmVyJTIwamFja2V0fGVufDB8fDB8fHwy"},
        {"name": "Cargo Pants", "category": "Bottoms", "price": 62000, "description": "Utility style cargo pants with multiple pockets. Practical and trendy.", "image_url": "https://images.unsplash.com/photo-1517445312882-56360c49747a?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8cGFudHN8ZW58MHx8MHx8fDI%3D"},
        {"name": "Polo Shirt", "category": "Tops", "price": 38000, "description": "Classic polo shirt in breathable cotton piqué. sporty and smart.", "image_url": "https://images.unsplash.com/photo-1625910515337-ccf30a9bf51e?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8cG9sb3xlbnwwfHwwfHx8Mg%3D%3D"},
        {"name": "Running Shoes", "category": "Shoes", "price": 95000, "description": "Lightweight running shoes with cushioned sole. Designed for speed and comfort.", "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8c2hvZXN8ZW58MHx8MHx8fDI%3D"},
        {"name": "Cardigan", "category": "Tops", "price": 45000, "description": "Soft knit cardigan with button closure. Great for layering over tees.", "image_url": "https://images.unsplash.com/photo-1434389677669-e08b4cac3105?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8Y2xvdGhlc3xlbnwwfHwwfHx8Mg%3D%3D"}
    ]

def main():
    print("Starting product expansion (Hardcoded)...")
    try:
        conn = get_db_connection()
        create_table_if_not_exists(conn)
        
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM shop_product")
        count = cur.fetchone()[0]
        print(f"Current product count: {count}")
        
        new_products = get_hardcoded_products()
        inserted_count = 0
        
        for p in new_products:
            try:
                cur.execute("""
                    INSERT INTO shop_product (name, category, price, description, image_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (p['name'], p['category'], p['price'], p['description'], p['image_url']))
                if cur.rowcount > 0:
                    inserted_count += 1
            except Exception as e:
                print(f"Error inserting {p.get('name')}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"Inserted {inserted_count} new products.")
            
        cur.close()
        conn.close()
        print("Done.")
        
    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    main()
