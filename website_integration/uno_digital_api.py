#!/usr/bin/env python3
import requests, json

website = 'https://betamanage.rullart.com'

head = {
  # 'Authorization': 'Basic YWRtaW46cnVsbGFAMTIzIQ==',
  'Content-Type': 'application/json'
}

# fetching sales order between datetime range
data = {
    'date_from': '2020-01-01 10:12',
    'date_to': '2020-02-03 20:10',
}
url = website + '/api/report/salesreport'
x = requests.get(url=url, params=data, auth=('admin', 'rulla@123!'))
# x = requests.post(url=url, data=final, headers=head)
text = x.text if not (x.text == '') else x.status_code
result = json.loads(text)
print(result)

# # fetching sales order starting from passed order ID
# data = {
#     'last_order_id': 3000
# }
# url = website + '/api/report/salesreport'
# x = requests.get(url=url, params=data, auth=('admin', 'rulla@123!'))
# text = x.text if not (x.text == '') else x.status_code
# result = json.loads(text)
# print(result)

# # get all product sizes
# data = {
# }
# url = website + '/api/report/allsize'
# x = requests.get(url=url, params=data, auth=('admin', 'rulla@123!'))
# text = x.text if not (x.text == '') else x.status_code
# result = json.loads(text)
# print(result)

# # get product info
# data = {
#     "productid": 271
# }
# url = website + '/api/report/productstock'
# x = requests.get(url=url, params=data, auth=('admin', 'rulla@123!'))
# text = x.text if not (x.text == '') else x.status_code
# result = json.loads(text)
# print(result)

# post product qty
data = {
    "productid": 271,
    "sizeid": 0,
    "warehouseid": 1,
    "qty": 11,
    "locationid": 1,
}
# print(str(data))
# data="{\"productid\": 271,\n\"sizeid\": 0,\n\"warehouseid\": 1,\n\"qty\": 50,\n\"locationid\": 1}"
url = website + '/api/report/productstock'
url = website + "/api/report/productstockupdate?productid=271&sizeid=0&warehouseid=1&qty=10&locationid=1"
# x = requests.post(url=url, params=data, data=data, json=data, headers=head, auth=('admin', 'rulla@123!'))
x = requests.request("POST", url, data=json.dumps(data), headers=head, auth=('admin', 'rulla@123!'))
text = x.text if not (x.text == '') else x.status_code
result = json.loads(text)
print(result)

# # ===========================================================================
# # ITEM DETAIL
# # url = website + '/api/menu/items/22193'
# url = website + '/api/trucks/self/menu/items/25562'
# x = requests.get(url=url, headers=header)
# text = x.text if not(x.text == '') else x.status_code
# text = json.loads(text)
# # qty = json.loads(text)['stockQty']
# qty = text['stockQty']
# print(qty)
#
# # ===========================================================================
# # LOGOUT
# url = website + '/auth/logout'
# x = requests.post(url=url, headers=header)
# if x.status_code == 200: print("Logout Successful")