from flask import Flask, render_template, request, jsonify
import pandas as pd
import re

app = Flask(__name__)
df = pd.read_csv('medicine_data.csv')
df1 = pd.read_csv('db_drug_interactions.csv')

# Preprocess interaction data into a lookup dictionary
interaction_lookup = {}

for _, row in df1.iterrows():
    drug1 = row['Drug 1'].strip().lower()
    drug2 = row['Drug 2'].strip().lower()
    interaction = row['Interaction'].strip()
    interaction_lookup.setdefault(drug1, []).append((drug2, interaction))
    interaction_lookup.setdefault(drug2, []).append((drug1, interaction))


@app.route('/', methods=['GET'])
def index():
    filtered_df = df.copy()
    query = request.args.get('query', '').lower()
    use_filter = request.args.get('use', '').lower()
    side_filter = request.args.get('side', '').lower()

    def clean_text(text):
        return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

    # Support multiple medicine keywords in query
    keywords = [kw.strip() for kw in re.split(r'[, ]+', query) if kw.strip()]

    # Define a score function for relevance
    def compute_score(row):
        score = 0
        for kw in keywords:
            if kw in clean_text(row['Medicine Name']):
                score += 1
            if kw in clean_text(row['Composition']):
                score += 1
        return score

    # Apply filters
    if keywords:
        df['score'] = df.apply(compute_score, axis=1)
        filtered_df = df[df['score'] > 0].copy()
    else:
        df['score'] = 0  # Default score column

    if use_filter:
        filtered_df = filtered_df[filtered_df['Uses'].str.lower().str.contains(use_filter)]
    if side_filter:
        filtered_df = filtered_df[filtered_df['Side_effects'].str.lower().str.contains(side_filter)]

    # Sort by relevance score and limit results
    filtered_df = filtered_df.sort_values(by='score', ascending=False).head(100)

    return render_template('index.html', data=filtered_df.to_dict(orient='records'))


@app.route('/interactions', methods=['POST'])
def get_interactions():
    composition = request.json.get('composition', '').lower()

    # Split composition by '+' if multiple ingredients
    ingredients = [re.sub(r'\s*\(.*?\)', '', part).strip().lower() for part in composition.split('+')]

    interactions = []
    for ingredient in ingredients:
        matches = interaction_lookup.get(ingredient, [])
        for match_drug, interaction_text in matches:
            interactions.append(f"Interaction with {match_drug}: {interaction_text}")

    return jsonify(interactions=interactions[:100])  # Limit to 100 interactions


if __name__ == '__main__':
    app.run(debug=True)
