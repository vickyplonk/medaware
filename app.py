from flask import Flask, render_template, request
import pandas as pd
import re

app = Flask(__name__)
df = pd.read_csv('medicine_data.csv')
df1 = pd.read_csv('db_drug_interactions.csv')

@app.route('/', methods=['GET', 'POST'])
def index():
    filtered_df = df.copy()
    query = request.args.get('query', '').lower()
    use_filter = request.args.get('use', '')
    side_filter = request.args.get('side', '')

    if query:
        filtered_df = filtered_df[
            filtered_df['Medicine Name'].str.lower().str.contains(query) |
            filtered_df['Composition'].str.lower().str.contains(query)
        ]
    if use_filter:
        filtered_df = filtered_df[filtered_df['Uses'].str.lower().str.contains(use_filter.lower())]
    if side_filter:
        filtered_df = filtered_df[filtered_df['Side_effects'].str.lower().str.contains(side_filter.lower())]

    # Create a dictionary to store interactions
    interactions_dict = {}

    # For each medicine in filtered data, look for interactions in df1
    for index, row in filtered_df.iterrows():
        medicine_name = row['Medicine Name'].strip().lower()
        interactions = []

        composition = row['Composition'].strip().lower()
        print(f"Searching for interactions with composition: {composition}")

        # Split composition by '+' or ',' to handle multiple ingredients
        components = re.split(r'\s*\+\s*|\s*,\s*', composition)

        for comp in components:
            # Remove dosage info in parentheses e.g. (325mg)
            base_name = re.sub(r'\s*\(.*?\)', '', comp).strip().lower()

            if not base_name:
                continue

            drug1_matches = df1[df1['Drug 1'].str.contains(base_name, case=False, na=False)]
            drug2_matches = df1[df1['Drug 2'].str.contains(base_name, case=False, na=False)]

            print(f"Component: {base_name}")
            print(f"Matches in Drug 1: {drug1_matches[['Drug 1', 'Drug 2', 'Interaction']]}")
            print(f"Matches in Drug 2: {drug2_matches[['Drug 1', 'Drug 2', 'Interaction']]}")

            for _, interaction_row in drug1_matches.iterrows():
                interactions.append(f"{base_name.title()} interacts with {interaction_row['Drug 2']}: {interaction_row['Interaction']}")

            for _, interaction_row in drug2_matches.iterrows():
                interactions.append(f"{base_name.title()} interacts with {interaction_row['Drug 1']}: {interaction_row['Interaction']}")

        interactions_dict[medicine_name] = interactions
        print(f"Interactions found for {composition}: {interactions}")


    return render_template('index.html', data=filtered_df.to_dict(orient='records'), interactions_dict=interactions_dict)

if __name__ == '__main__':
    app.run(debug=True)
