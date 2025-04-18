import os
from flask import Flask, render_template, request, jsonify
from google.cloud import vision
import pandas as pd
import re
from werkzeug.utils import secure_filename
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load datasets
med_df = pd.read_csv('medicine_data.csv')
interactions_df = pd.read_csv('db_drug_interactions.csv')
uses_df = pd.read_csv('uses_term_counts.csv')

# Get top 200 use terms for sidebar filtering
top_uses_terms = uses_df['Term'].head(200).tolist()

# Prepare autocomplete list (brand + composition names)
brand_names = sorted(med_df['Medicine Name'].dropna().unique())
composition_names = sorted(med_df['Composition'].dropna().unique())
autocomplete_list = sorted(set(brand_names + composition_names))

# Build interaction lookup dictionary
interaction_lookup = {}
for _, row in interactions_df.iterrows():
    drug1 = row['Drug 1'].strip().lower()
    drug2 = row['Drug 2'].strip().lower()
    interaction_text = row['Interaction'].strip()

    interaction_lookup.setdefault(drug1, []).append((drug2, interaction_text))
    interaction_lookup.setdefault(drug2, []).append((drug1, interaction_text))


# Configure upload folder
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_text(text):
    """Utility to clean and lowercase strings."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

@app.get('/')
def index():
    query = request.args.get('query', '').lower()
    use_filter = request.args.get('use', '').lower()
    side_filter = request.args.get('side', '').lower()

    # Break query into cleaned keywords
    keywords = [clean_text(kw.strip()) for kw in re.split(r'[, ]+', query) if kw.strip()]

    # Scoring function to rank relevance
    def compute_score(row):
        score = 0
        name = clean_text(row['Medicine Name'])
        composition = clean_text(row['Composition'])

        # Remove units like 'mg', 'ml' etc. and punctuation
        cleaned_ingredients = re.sub(r'\b(mg|ml|mcg|g|%)\b', '', composition)
        ingredients = [ing.strip() for ing in cleaned_ingredients.split('+')]

        for kw in keywords:
            if kw in name:
                score += 2
            for ing in ingredients:
                if kw in ing:
                    score += 1
        return score

    med_df['score'] = med_df.apply(compute_score, axis=1)

    # Filter by search query
    if keywords:
        filtered = med_df[med_df['score'] > 0].copy()
    else:
        filtered = med_df.copy()

    # Apply use and side-effect filters
    if use_filter:
        filtered = filtered[filtered['Uses'].str.lower().str.contains(use_filter)]
    if side_filter:
        filtered = filtered[filtered['Side_effects'].str.lower().str.contains(side_filter)]

    # Sort by score and limit to top 100
    filtered = filtered.sort_values(by='score', ascending=False).head(100)

    return render_template('index.html', data=filtered.to_dict(orient='records'), uses_terms=top_uses_terms)

@app.post('/interactions')
def get_interactions():
    composition = request.json.get('composition', '').lower()
    ingredients = [re.sub(r'\s*\(.*?\)', '', part).strip().lower() for part in composition.split('+')]

    interactions = []
    for ing in ingredients:
        matches = interaction_lookup.get(ing, [])
        for other_drug, interaction_text in matches:
            interactions.append(f"Interaction with {other_drug}: {interaction_text}")

    return jsonify(interactions=interactions[:100])  # Limit for display

@app.get('/autocomplete')
def autocomplete():
    query = request.args.get('term', '').lower()
    matches = [item for item in autocomplete_list if query in item.lower()]
    return jsonify(matches[:20])

# Route to serve the upload form
@app.get('/upload')
def upload():
    return render_template('upload.html')

# Route to handle the file upload and text recognition
@app.post('/upload')
def upload_prescription():
    print(request.files)
    client = genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))
    myfile = client.files.upload(file=request.files['prescription'])
    print(f"{myfile=}")

    # result = client.models.generate_content(
    #     model="gemini-2.0-flash",
    #     contents=[
    #         myfile,
    #         "\n\n",
    #         "Please extract from the image each drug name or the composition without the dosage in the format of JSON like {'Drug':'Text'}",
    #     ],
    # )
    # print(f"{result.text=}")
    # return {"output": result.text}

    # Match recognized text with medicines
   # matching_medicines = [med for med in med_df['Medicine Name'].unique() if clean_text(med) in clean_text(recognized_text)]

    #return render_template('upload.html', recognized_text=recognized_text, matching_medicines=matching_medicines)


if __name__ == '__main__':
    app.run(debug=True)
