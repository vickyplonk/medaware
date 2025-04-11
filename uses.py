import pandas as pd
import re
from collections import Counter

df = pd.read_csv('medicine_data.csv')
# Function to clean and split use phrases
def extract_use_terms(uses_string):
    if pd.isna(uses_string):
        return []

    # Extract everything inside parentheses
    parens = re.findall(r'\((.*?)\)', uses_string)
    
    # Remove parentheses content from main text
    uses_clean = re.sub(r'\(.*?\)', '', uses_string)

    # Split by common prefixes and normalise
    terms = re.split(r'Treatment of |treatment of |Prevention of |prevention of ', uses_clean)
    terms = [term.strip().lower().replace('&', 'and') for term in terms if term.strip()]

    # Add extracted parenthesis terms as separate entries
    parens = [p.strip().lower() for p in parens]
    
    return terms + parens

# Extract and flatten all use terms from the DataFrame
all_use_terms = df['Uses'].dropna().apply(extract_use_terms)
flat_terms = [term for sublist in all_use_terms for term in sublist]

# Count term frequencies
term_counter = Counter(flat_terms)

# Optionally, save term frequencies to CSV
term_df = pd.DataFrame(term_counter.items(), columns=['Term', 'Count']).sort_values(by='Count', ascending=False)
term_df.to_csv('uses_term_counts.csv', index=False)

# Add the most frequent use term for each row for sorting
def most_common_use_in_row(uses_string):
    terms = extract_use_terms(uses_string)
    if not terms:
        return ''
    return max(terms, key=lambda x: term_counter.get(x, 0))

df['Primary_Use'] = df['Uses'].apply(most_common_use_in_row)
df['Use_Frequency'] = df['Primary_Use'].apply(lambda x: term_counter.get(x, 0))

# Sort the DataFrame by most common use frequency
df_sorted = df.sort_values(by='Use_Frequency', ascending=False)

# Optional: Save or return
df_sorted.to_csv('sorted_by_use_frequency.csv', index=False)