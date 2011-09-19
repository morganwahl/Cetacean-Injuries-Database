import sys
from pprint import pprint

from django.test.client import Client
from cetacean_incidents.apps.csv_import.views import import_stranding_csv

c = Client()
c.login(username='import_user', password='resu_tropmi')

filename = sys.argv[1]
csv_file = open(filename)

response = c.post(
    path= '/csv_import/strandings',
    follow=True,
    data= {
        'csv_file': csv_file,
        'test_run': True,
    },
)
csv_file.close()

pprint({
    'status_code': response.status_code,
    'redirect_chain': response.redirect_chain,
    #'context': response.context,
})

