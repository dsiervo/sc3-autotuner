import MySQLdb

db_ip = "10.100.100.232"
db = MySQLdb.connect(host=db_ip,
                    user='consulta',
                    passwd='consulta',
                    db='seiscomp3')

cursor = db.cursor()

query_str = open('coords_query.sql').read()
query = query_str.format(net='CM', sta='BRJC', loc='00')
print(query)

cursor.execute(query)

print(cursor.fetchone())