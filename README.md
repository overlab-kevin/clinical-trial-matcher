# Clinical Trial Matcher

A tool that evaluates clinical trials against patient data using GPT to estimate eligibility and potential benefits.

## Dislaimer
This software is provided for research and informational purposes only. It is not intended to be a substitute for professional medical advice, diagnosis, or treatment. The eligibility estimates and benefit scores provided by this tool are generated using AI and should not be considered medical recommendations. Always consult with qualified healthcare professionals regarding clinical trial participation.

The creators and contributors of this tool make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability, or availability of the tool or the information it provides. Any reliance you place on such information is strictly at your own risk.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set your OpenAI API key: `export OPENAI_API_KEY="your-key-here"`

## Usage

1. Prepare your input files:
   - Patient data file (text file with patient information)
   - Trials data file (JSON from clinicaltrials.gov)

2. Process trials using either single-stage or two-stage approach:

   Single-stage processing:
   ```bash
   python run.py patient_data.txt trials_data.json output.json gpt-4o
   ```

   Two-stage processing (for cost efficiency):
   ```bash
   # Stage 1: Process all trials with a simpler model
   python run.py patient_data.txt trials_data.json initial_output.json gpt-4o-mini

   # Stage 2: Process top N trials with a more sophisticated model
   python run.py patient_data.txt trials_data.json final_output.json gpt-4o \
     --previous_output initial_output.json --num_of_trials 20
   ```

   Note that if the output JSON file already contains processed trials, these processed trials will be skipped. This allows you to resume the process if it is halted or to update a previously processed set of trials with new trials.

3. Convert results to CSV:
   ```bash
   python convert_to_csv.py output.json output.csv
   ```
   The CSV file can be imported into spreadsheet software like Google Sheets for easy viewing and analysis.

## Input Data

### Getting Trial Data
1. Visit clinicaltrials.gov
2. Search for relevant conditions/diseases. Note: it may be important to keep the search broad and then use the two-stage method above so relevant trials are not missed.
3. Use filters like "recruiting" and "not yet recruiting"
4. Download the search results as JSON

### Patient Data
Create a text file with relevant patient information, including:
- Diagnosis
- Current condition
- Treatment history
- Any specific requirements, goals, or preferences

## Output

The tool generates:
- JSON file with detailed trial evaluations
- CSV file with organized results including:
  - Trial ID and link
  - Treatment type and drug
  - Eligibility probability
  - Clinical benefit score
  - Total score
  - Location and start date

## Citation

If you use this tool in your research or work, please cite it as:

```bibtex
@software{clinical_trial_matcher,
  author = {[Kevin Murray]},
  title = {Clinical Trial Matcher},
  year = {2024},
  url = {https://github.com/overlab-kevin/clinical-trial-matcher},
  version = {1.0.0}
}
```

Or in text format:

Kevin Murray. (2024). Clinical Trial Matcher (Version 1.0.0) [Computer software]. https://github.com/overlab-kevin/clinical-trial-matcher
