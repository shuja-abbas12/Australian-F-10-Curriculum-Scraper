import pandas as pd

# Load the data CSV from the working directory
df = pd.read_csv('data.csv')

# Remove rows where Status is "no_data"
filtered = df[df['Status'] != 'no_data']

# Drop the two no-longer-needed columns
final_df = filtered.drop(columns=['Status', 'UTC'])

# Save to a new file
final_df.to_csv('FinalData.csv', index=False)
