from flask import Flask, render_template, request
import pandas as pd

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
        medicine_name = row['Medicine Name']
        interactions = []

        # Find interactions for the current medicine
        interaction_rows = df1[(df1['Drug 1'].str.lower() == medicine_name.lower()) | 
                               (df1['Drug 2'].str.lower() == medicine_name.lower())]
        
        # Add interaction descriptions to the list
        for _, interaction_row in interaction_rows.iterrows():
            if interaction_row['Drug 1'].lower() == medicine_name.lower():
                interactions.append(f"Interaction with {interaction_row['Drug 2']}: {interaction_row['Interaction']}")
            elif interaction_row['Drug 2'].lower() == medicine_name.lower():
                interactions.append(f"Interaction with {interaction_row['Drug 1']}: {interaction_row['Interaction']}")
        
        interactions_dict[medicine_name] = interactions

    return render_template('index.html', data=filtered_df.to_dict(orient='records'), interactions_dict=interactions_dict)

if __name__ == '__main__':
    app.run(debug=True)
