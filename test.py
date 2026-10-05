import requests

response = requests.get("https://www.cookwell.com/robots.txt")
print(response.text)