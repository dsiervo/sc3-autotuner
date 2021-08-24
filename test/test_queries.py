import MySQLdb
from icecream import ic
ic.configureOutput(prefix='debug| ')

db = MySQLdb.connect(host='10.100.100.232',
                     user='consulta',
                     passwd='consulta',
                     db='seiscomp3')

cursor = db.cursor()

# test picks_query2.sql
query_str = open('picks_query2.sql').read()

dic_data = {'sta_lat': 6.592, 'sta_lon': -73.18,
            'ti': '2020-01-01', 'tf': '2020-02-01',
            'net': 'CM', 'sta': 'BAR2',
            'radius': 111*2}
query = query_str.format(**dic_data)
ic(query)

cursor.execute(query)

data = [list(row) for row in cursor.fetchall()]
ic(data[0])

# keeping with the second column in data
id_list = [row[1] for row in data]
# keeping with p times in data
p_times = [row[2:5] for row in data]
# keeping with s times in data
s_times = [row[5:8] for row in data]

ic(id_list[0])
ic(p_times[0])
ic(s_times[0])