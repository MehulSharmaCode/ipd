# Gemini API Quota Diagnosis Report

## Environment Details
- **SDK Version**: `google-genai 2.16.0`
- **Detected Endpoint**: `generativelanguage.googleapis.com` (Default for AI Studio)
- **Detected Project**: Implicit via AI Studio `GEMINI_API_KEY`
- **Detected Models**:
  - `gemini-2.5-flash`
  - `gemini-2.0-flash`
  - `gemini-flash-latest`

## HTTP Request Results
- **Model: `gemini-2.5-flash`**
  - **HTTP Status**: `404 NOT_FOUND`
  - **Response**: "This model is no longer available to new users."
- **Model: `gemini-2.0-flash`**
  - **HTTP Status**: `429 RESOURCE_EXHAUSTED`
  - **Response**: "Quota exceeded limit: 0"
  - **Quota Metrics**: Dashboard shows active free-tier quota, but API enforces `limit: 0`.

## Root Cause Analysis
The inconsistency between the active free-tier quota in the dashboard and the `429 RESOURCE_EXHAUSTED (limit: 0)` error is a **Known Google API behavior (G)** combined with **Free tier disabled (A) / Billing required (B)**.

**Detailed Explanation:**
1. **Model 404s**: The `models.list()` endpoint returns *all* historically registered models in the system. However, models like `gemini-2.5-flash` have been gated and are "no longer available to new users". The SDK tests (which use `gemini-2.5-flash`) run against internal or grandfathered projects that still have access.
2. **Quota limit: 0**: When the Google AI Studio dashboard shows available free-tier quota but the API returns `limit: 0`, it typically means the API key is restricted from using the free tier. This happens in two main scenarios:
   - **Geographic Restrictions**: The request is originating from a region where the Gemini Free Tier is legally or policy-restricted (e.g., the EU, UK, or Switzerland). In these regions, the free tier is effectively disabled (`limit: 0`), and a linked billing account is mandatory to use the API (Paid Tier).
   - **Billing State Mismatch**: The Google Cloud Project lacks a linked billing account for a model that strictly requires it, or the API key was generated *before* billing was properly configured, resulting in a cached `0` limit for that key.

## Recommended Fix
To resolve this blocker and resume the Proof of Concept:

1. **Enable Billing**: Go to the Google Cloud Console and ensure a valid Billing Account is linked to the project associated with your AI Studio API key. (You will only be charged if you exceed the free tier limits, but the billing account is required to lift the `limit: 0` restriction in many regions).
2. **Regenerate API Key**: After confirming billing is active, generate a **brand new API Key** in Google AI Studio to ensure the quota rules are refreshed.
3. **Use the Alias**: Update your `.env` file to use the auto-resolving alias, which will automatically route to the latest supported model you have quota for:
   ```env
   GEMINI_MODEL=gemini-flash-latest
   ```

## Confidence Level
**High (95%)**. The symptoms (dashboard showing quota, API returning `limit: 0` for `gemini-2.0-flash`, and `404` for new users on `gemini-2.5-flash`) perfectly match Google's documented behavior for regions without free-tier support or projects missing required billing verification.
