from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import requests

app = FastAPI()

@app.get("/fetch-studies")
def fetch_studies(
    sponsors: str = Query(..., description="Comma and space-separated list of lead sponsors"),
    email: str = Query(..., description="User email address for identification/logging (not used for matching in this example)")
):
    try:
        # Parse sponsors
        sponsor_list = [s.strip() for s in sponsors.split(",") if s.strip()]
        if not sponsor_list:
            return JSONResponse(status_code=400, content={"error": "No sponsors provided."})

        # Construct sponsor filters
        sponsor_filters = " OR ".join(f'AREA[LeadSponsor]"{"".join(s)}"' for s in sponsor_list)

        # Date range: last 24 hours (UTC)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=1)
        date_filter = f'AREA[LastUpdatePostDate]RANGE[{start_date},{end_date}]'

        # Build query
        query_term = f"({sponsor_filters}) AND {date_filter}"

        # Call API
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.term": query_term,
            "sort": "LastUpdatePostDate:desc",
            "pageSize": 50
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Format output
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

        return {"email": email, "results": results or "No new studies found."}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
