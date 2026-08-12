import random, os
from faker import Faker
import mysql.connector

print(f"MYSQL host is {os.environ.get('MYSQL_HOST')}")

fake = Faker()
conn = mysql.connector.connect(
    host=os.environ.get('MYSQL_HOST'), user=os.environ.get('MYSQL_USER'), 
    password=os.environ.get('MYSQL_PASS'), database="demo", port=os.environ.get('MYSQL_PORT')
)
cur = conn.cursor()

print(f"MYSQL host is {os.environ.get('MYSQL_HOST')}")

models = ["A320neo","A350-900","B737-MAX8","B787-9"]
categories = ['engine','avionics','fuselage','landing_gear','hydraulics','electrical','interior']
suppliers = ["Rolls-Royce","GE Aviation","Honeywell","Safran","Collins Aerospace","Thales"]
results = ['pass','pass','pass','fail','rework']  # weighted toward pass
defects = ['CRK-01','CORR-04','TOL-12','FST-07','ELEC-03']

rows = []
for _ in range(2000):
    res = random.choice(results)
    rows.append((
        f"EI-{fake.lexify('???').upper()}",
        random.choice(models),
        random.choice(categories),
        random.choice(suppliers),
        fake.date_between('-2y','today'),
        res,
        'NONE' if res == 'pass' else random.choice(defects),
        round(random.uniform(1, 300), 2),
    ))

cur.executemany(
    """INSERT INTO quality_inspections
       (tail_number,model_name,component_category,supplier_name,inspection_date,result,defect_code,labor_hours)
       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
    rows,
)
conn.commit()
cur.close()
conn.close()
print(f"Inserted {len(rows)} rows.")