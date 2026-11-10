import json

with open(r"C:\Users\Матвей\Documents\GitHub\AI-File-Sorter\src\agent\directory_agent\mult_score.json") as f:
    total = sum(json.load(f))

print(total)