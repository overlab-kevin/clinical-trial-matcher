import json
import os
import openai
from openai import OpenAI, RateLimitError, BadRequestError, APIError
import argparse
import time
from tqdm import tqdm

def load_trials(trials_file):
    with open(trials_file, 'r') as f:
        return json.load(f)

def load_patient_data(patient_file):
    with open(patient_file, 'r') as f:
        return f.read()

def load_processed_trials(output_file):
    done_trials = set()
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            try:
                output_data = json.load(f)
                for entry in output_data:
                    done_trials.add(entry['trial_id'])
            except json.JSONDecodeError:
                print(f"Warning: Output file {output_file} is not valid JSON or empty.")
    return done_trials

def generate_prompt(trial_data, patient_data, strip_contacts_locations=False):
    if strip_contacts_locations:
        trial_data['protocolSection']['contactsLocationsModule'] = ''

    trial_details = json.dumps(trial_data, indent=2)
    
    prompt = f"""
    Given the patient's condition, please act as a highly relevant medical expert or team of experts and evaluate the relevance of a clinical trial for the patient.

    Here is a patient's data: 
    {patient_data}
    
    Here are the full details of a clinical trial:
    {trial_details}
    
    Please evaluate the relevance of this clinical trial for the patient and provide a response in the following JSON format:

    {{
        "unclear_criteria": <list of inclusion/exclusion criteria that cannot be definitively determined from the patient data>,
        "eligibility_probability": <probability (0-100) that the patient currently meets all eligibility criteria>,
        "clinical_benefit_score": <Score up to 100. Score should be in terms of how relevant medical experts would estimate the medical benefit to the patient, especially in regard to any goals listed in the patient data. Consider all information available, including how recent the study is, how many participants there are, the type of treatment, the phase of the trial, and the prestige of who is making/providing the treatment.>,
        "total_score": <weighted score based on clinical benefit score and eligibility probability (clinical_benefit_score * eligibility_probability / 100)>,
        "reasoning": <brief reasoning for the clinical benefit score and eligibility probability>,
        "treatment_type": <1-6 word summary of the treatment type (e.g. KRAS inhibitor)>,
        "number_of_patients": <number of patients expected in the trial>,
        "trial_phase": <phase or phases of the trial>,
        "start_date": <expected start date of the trial>,
        "location": <the location or list of locations of the trial>,
        "link": <hyperlink to the trial on clinicaltrials.gov>,
        "drug": <name of the drug used in the trial, if applicable>
    }}

    Please ensure that the response is solely a valid JSON string, in this format, and nothing else. The complete response will be immediately parsed as such. Thank you!
    """
    return prompt

def get_gpt_response(prompt, client, model, max_retries=5, initial_delay=1):
    """
    Get response from GPT with rate limit handling and exponential backoff.
    
    Args:
        prompt: The prompt to send to GPT
        client: OpenAI client instance
        model: Model name to use
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
    """
    attempt = 0
    current_delay = initial_delay

    while attempt < max_retries:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            attempt += 1
            if attempt == max_retries:
                print(f"Rate limit exceeded after {max_retries} attempts. Skipping.")
                return None
                
            # Calculate delay with exponential backoff
            sleep_time = current_delay * (2 ** (attempt - 1))  # exponential backoff
            print(f"Rate limit hit. Waiting {sleep_time} seconds before retry {attempt}/{max_retries}")
            time.sleep(sleep_time)
            
        except BadRequestError as e:
            print(f"Bad request: {e}")
            return None
            
        except APIError as e:
            attempt += 1
            if attempt == max_retries:
                print(f"API error persisted after {max_retries} attempts. Skipping.")
                return None
                
            sleep_time = current_delay * (2 ** (attempt - 1))
            print(f"API error occurred. Waiting {sleep_time} seconds before retry {attempt}/{max_retries}")
            time.sleep(sleep_time)

    return None

def clean_gpt_response(response_text):
    if response_text.startswith("```json") and response_text.endswith("```"):
        response_text = response_text[7:-3].strip()
    return response_text

def parse_gpt_response(response_text):
    try:
        cleaned_response = clean_gpt_response(response_text)
        parsed_response = json.loads(cleaned_response)
        
        # Validate score ranges
        if "eligibility_probability" in parsed_response:
            prob = parsed_response["eligibility_probability"]
            if not isinstance(prob, (int, float)) or prob < 0 or prob > 100:
                print("Warning: eligibility_probability out of valid range")
                parsed_response["eligibility_probability"] = None
                
        if "clinical_benefit_score" in parsed_response:
            score = parsed_response["clinical_benefit_score"]
            if not isinstance(score, (int, float)) or score < 0 or score > 100:
                print("Warning: clinical_benefit_score out of valid range")
                parsed_response["clinical_benefit_score"] = None
                
        return parsed_response
        
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response. Returning empty structure.")
        return {
            "total_score": None,
            "clinical_benefit_score": None,
            "unclear_criteria": None,
            "eligibility_probability": None,
            "reasoning": None,
            "treatment_type": None,
            "number_of_patients": None,
            "trial_phase": None,
            "start_date": None,
            "location": None,
            "link": None,
            "drug": None
        }

def write_to_output_file(output_file, trial_id, gpt_response):
    output_data = []
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            try:
                output_data = json.load(f)
            except json.JSONDecodeError:
                pass

    output_data.append({
        "trial_id": trial_id,
        "gpt_response": gpt_response
    })

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

def select_top_trials(previous_output, num_of_trials):
    with open(previous_output, 'r') as f:
        output_data = json.load(f)
    sorted_trials = sorted(output_data, key=lambda x: x["gpt_response"].get("total_score") or 0, reverse=True)
    return sorted_trials[:num_of_trials]

def process_trials(trials_data, patient_data, client, output_file, model, previous_output=None, num_of_trials=None):
    done_trials = load_processed_trials(output_file)
    trials_to_process = trials_data

    if previous_output and num_of_trials:
        print(f"Selecting top {num_of_trials} trials from previous output {previous_output}")
        top_trials = select_top_trials(previous_output, num_of_trials)
        trials_to_process = [trial for trial in trials_data if trial['protocolSection']['identificationModule'].get('nctId') in {t['trial_id'] for t in top_trials}]

    # Initialize progress bar
    pbar = tqdm(trials_to_process, desc="Processing trials")
    
    for trial in pbar:
        trial_id = trial['protocolSection']['identificationModule'].get('nctId', 'unknown_id')
        pbar.set_postfix({'Trial': trial_id}, refresh=True)

        if trial_id in done_trials:
            pbar.write(f"Skipping trial {trial_id}, already processed.")
            continue

        prompt = generate_prompt(trial, patient_data)
        gpt_response = get_gpt_response(prompt, client, model)

        if gpt_response is None:
            pbar.write(f"Trying again with stripped contacts/locations for trial {trial_id}.")
            prompt = generate_prompt(trial, patient_data, strip_contacts_locations=True)
            gpt_response = get_gpt_response(prompt, client, model)

        if gpt_response is None:
            pbar.write(f"Skipping trial {trial_id} due to error.")
            continue

        structured_response = parse_gpt_response(gpt_response)
        write_to_output_file(output_file, trial_id, structured_response)

        # Update progress bar with more details
        if structured_response.get('total_score') is not None:
            pbar.set_postfix({
                'Trial': trial_id,
                'Score': f"{structured_response['total_score']:.1f}"
            }, refresh=True)

        time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process clinical trials with GPT")
    parser.add_argument("patient", type=str, help="Path to patient data file")
    parser.add_argument("trials", type=str, help="Path to clinical trials JSON file")
    parser.add_argument("output", type=str, help="Path to output JSON file")
    parser.add_argument("model", type=str, help="OpenAI model to use", default="gpt-4o-mini")
    parser.add_argument("--previous_output", type=str, help="Path to previous output JSON file", default=None)
    parser.add_argument("--num_of_trials", type=int, help="Number of top trials to process", default=None)
    args = parser.parse_args()

    trials_data = load_trials(args.trials)
    patient_data = load_patient_data(args.patient)
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    process_trials(trials_data, patient_data, client, args.output, args.model, args.previous_output, args.num_of_trials)
    print(f"\nAll trials processed. Results saved to {args.output}")
