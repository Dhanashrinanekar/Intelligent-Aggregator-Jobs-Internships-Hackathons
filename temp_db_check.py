import psycopg2
from pprint import pprint

conn = psycopg2.connect(host='localhost', dbname='job_aggregator', user='postgres', password='Pass123')
cur = conn.cursor()
cur.execute("SELECT id, company_name, role, opportunity_type, skills, experience_required, location, salary, description, application_link FROM opportunities ORDER BY id DESC LIMIT 10")
rows = cur.fetchall()
pprint(rows)
conn.close()
