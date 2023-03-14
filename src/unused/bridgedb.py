import bridgedbpy
import requests
import timeit


def main():
    with open("oout.txt", "r") as f:
        proteins = f.read()
    url = "https://webservice.bridgedb.org/"
    batch_request = url + "{org}/xrefsBatch/{source}{}"
    mapping_available = "{org}/isMappingSupported/{source}/{target}"
    query = url + mapping_available.format(org="Homo sapiens", source="H", target="S")
    requests.get(query).text
    query = batch_request.format("?dataSource=S", org="Homo sapiens", source="H")
    response = requests.post(query, data=proteins)
    # print(response.text)


time = timeit.timeit(main, number=5)
print(time)
