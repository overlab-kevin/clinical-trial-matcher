import json
import csv
import argparse

def load_json(input_file):
    with open(input_file, 'r') as f:
        return json.load(f)

def json_to_csv(json_data, output_file):
    # Define CSV column headers to match new structure
    fieldnames = [
        'trial_id', 
        'link', 
        'treatment_type', 
        'drug', 
        'number_of_patients', 
        'trial_phase', 
        'start_date', 
        'location',
        'eligibility_probability',
        'clinical_benefit_score',
        'total_score',
        'unclear_criteria',
        'reasoning'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for trial in json_data:
            trial_id = trial.get('trial_id', 'unknown_id')
            gpt_response = trial.get('gpt_response', {})

            # Handle None values and ensure .replace() works on strings
            unclear_criteria = gpt_response.get('unclear_criteria', '')
            reasoning = gpt_response.get('reasoning', '')

            # Convert unclear_criteria list to string if necessary
            if isinstance(unclear_criteria, list):
                unclear_criteria = '; '.join(unclear_criteria)

            # Write the row to the CSV
            writer.writerow({
                'trial_id': trial_id,
                'link': gpt_response.get('link', ''),
                'treatment_type': gpt_response.get('treatment_type', ''),
                'drug': gpt_response.get('drug', ''),
                'number_of_patients': gpt_response.get('number_of_patients', ''),
                'trial_phase': gpt_response.get('trial_phase', ''),
                'start_date': gpt_response.get('start_date', ''),
                'location': gpt_response.get('location', ''),
                'eligibility_probability': gpt_response.get('eligibility_probability', ''),
                'clinical_benefit_score': gpt_response.get('clinical_benefit_score', ''),
                'total_score': gpt_response.get('total_score', ''),
                'unclear_criteria': unclear_criteria.replace('\n', ' ') if unclear_criteria else '',
                'reasoning': reasoning.replace('\n', ' ') if reasoning else ''
            })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JSON to CSV")
    parser.add_argument("input", type=str, help="Path to the input JSON file")
    parser.add_argument("output", type=str, help="Path to the output CSV file")
    args = parser.parse_args()

    json_data = load_json(args.input)
    json_to_csv(json_data, args.output)
    print(f"Saved CSV to {args.output}")
