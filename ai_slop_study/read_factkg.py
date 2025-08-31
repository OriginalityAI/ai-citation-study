import pickle

with open("factkg/factkg_dev.pickle", "rb") as f:
    obj = pickle.load(f)

claims = list(obj.keys())
written_claims = [c for c in claims if 'written' in obj[c]['types']]

print(obj[written_claims[0]])

print(len(claims))
print(len(written_claims))

# print(written_claims[:100])
