# analytics_engine.py
import re
from llm_service import call_llm
import prompts

import json
import re

import json
import re
import prompts # Make sure this is at the top of your file!

import json
import re
import prompts
from llm_service import call_llm

def categorize_review(review_text):
    """
    Sends the review to the unified LLM service and safely extracts the category from the JSON response.
    """
    try:
        # 1. Format the user message
        user_msg = f"<review>{review_text}</review>"
        
        # 2. Call your centralized LLM service (passing the prompts and strict temperature)
        raw_output = call_llm(
            system_prompt=prompts.CATEGORIZATION_SYSTEM_PROMPT, 
            user_message=user_msg, 
            temperature=0.0
        )

        # 3. Aggressive JSON Extraction (ignores markdown and chatter)
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)
        
        if match:
            json_string = match.group(0) 
            parsed_data = json.loads(json_string)
            
            # Safely extract the category
            return parsed_data.get("category", "GENERAL_INQUIRY")
        #if "category" in parsed_data: return parsed_data["category"]else: return "GENERAL_INQUIRY"

            
        else:
            print(f"⚠️ Warning: No JSON brackets found in Llama 3 output. Raw: {raw_output}")
            return "GENERAL_INQUIRY"
            
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON Parse Error: {e} | Raw output: {raw_output}")
        return "GENERAL_INQUIRY"
    except Exception as e:
        print(f"⚠️ Execution Error: {e}")
        return "GENERAL_INQUIRY"

def generate_diagnostic_sql(complaint_category):
    try:
        user_msg = f"Investigate the root cause for the Complaint Theme: {complaint_category}"

        raw_output = call_llm(
            prompts.SQL_SYSTEM_PROMPT,
            user_msg,
            temperature=0.0
        )

        print("RAW OUTPUT:")
        print(raw_output)

        match = re.search(
            r'(?is)\bSELECT\b.*?(?:;|$)',
            raw_output
        )

        if match:
            clean_sql = match.group(0).strip()
            print("CLEAN SQL:")
            print(clean_sql)
            return clean_sql

        return "ERROR_GENERATING_SQL"

    except Exception as e:
        print(f"SQL Generation Error: {e}")
        return "ERROR_GENERATING_SQL"
    
def generate_business_insight(complaint_theme, metrics_df):
    try:
        data_string = metrics_df.to_string(index=False)
        user_message = f"The top user complaint is '{complaint_theme}'. Exact metrics:\n{data_string}\n\nPlease generate the Executive Summary."
        return call_llm(prompts.INSIGHT_SYSTEM_PROMPT, user_message, temperature=0.1)
    except Exception as e:
        return f"Error generating insight: {e}"