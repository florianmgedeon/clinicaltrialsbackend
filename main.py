from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import requests
import traceback

app = FastAPI()

@app.get("/fetch-studies")
def fetch_studies(
    sponsors: str = Query(..., description="Comma and space-separated list of lead sponsors"),
    email: str = Query(..., description="User email address for identification/logging")
):
    try:
        print(f"📥 Request received - Email: {email}, Sponsors: {sponsors}")

        # Parse sponsor names
        sponsor_list = [s.strip() for s in sponsors.split(",") if s.strip()]
        if not sponsor_list:
            return JSONResponse(status_code=400, content={"error": "No sponsors provided."})

        # Build query for sponsor filter
        sponsor_filters = " OR ".join(f'AREA[LeadSponsor]"{"".join(s)}"' for s in sponsor_list)

        # Date range: last 24 hours in UTC
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=1)
        date_filter = f'AREA[LastUpdatePostDate]RANGE[{start_date},{end_date}]'

        # Final combined query
        query_term = f"({sponsor_filters}) AND {date_filter}"

        # API call
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.term": query_term,
            "sort": "LastUpdatePostDate:desc",
            "pageSize": 50
        }

        print(f"🔍 Fetching from ClinicalTrials.gov API with query: {query_term}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Parse studies
        results = []
        for study in data.get("studies", []):
            nct_id = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId", "")
            sponsor = study.get("protocolSection", {}).get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "")
            if nct_id:
                results.append({
                    "nctId": nct_id,
                    "leadSponsor": sponsor,
                    "link": f"https://clinicaltrials.gov/study/{nct_id}"
                })

        print(f"✅ Found {len(results)} study/studies for {email}")

        return {
            "email": email,
            "results": results if results else "No new studies found."
        }

    except Exception as e:
        traceback_str = traceback.format_exc()
        print("❌ Error occurred:\n", traceback_str)
        return JSONResponse(status_code=500, content={
            "error": str(e),
            "trace": traceback_str
        })
