import csv
import random
import uuid
from datetime import datetime, timedelta

# Define output file name
output_file = 'sample_data.csv'

# Define number of rows
num_rows = 100

# Define column headers and their types
headers = [
    'id',              # STRING (UUID)
    'name',            # STRING
    'age',             # INTEGER
    'score',           # FLOAT
    'is_active',       # BOOLEAN
    'signup_date',     # DATE (YYYY-MM-DD)
    'last_login',      # TIMESTAMP (ISO 8601)
    'country',         # STRING
    'num_purchases',   # INTEGER
    'account_balance'  # FLOAT
]

names = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Heidi']
countries = ['US', 'UK', 'CA', 'DE', 'FR', 'AU', 'JP', 'IN']

def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))

with open(output_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

    for _ in range(num_rows):
        signup = random_date(datetime(2018, 1, 1), datetime(2024, 12, 31))
        last_login = signup + timedelta(days=random.randint(1, 500))

        row = [
            str(uuid.uuid4()),                             # id
            random.choice(names),                          # name
            random.randint(18, 70),                        # age
            round(random.uniform(0, 100), 2),              # score
            random.choice([True, False]),                  # is_active
            signup.date().isoformat(),                     # signup_date
            last_login.isoformat(),                        # last_login
            random.choice(countries),                      # country
            random.randint(0, 50),                         # num_purchases
            round(random.uniform(100.0, 10000.0), 2)       # account_balance
        ]
        writer.writerow(row)

print(f'Data written to {output_file}')
