import pandas as pd

# Load CSV
df = pd.read_csv("review_table (2).csv")

# Convert to JSON
df.to_json("review_table.json", orient="records", indent=4)

print("Converted successfully!")