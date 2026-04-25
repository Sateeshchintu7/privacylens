import os
from google import genai
client = genai.Client(api_key='AIzaSyA_Y_QsytQzwhBCIGvCBMj-kQs_pw2EN0Y')
for m in client.models.list():
    print(m.name)
