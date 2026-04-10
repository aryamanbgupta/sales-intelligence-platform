# Task: AI-Powered B2B Sales Intelligence Platform for Roofing Distributors

## Business Context

A **roofing distributor** needs a platform to help their sales team find and engage **roofing contractors** as potential customers. The distributor sells roofing materials (shingles, underlayment, accessories) to contractors who install them on residential projects.

**Value chain:** GAF (manufacturer) → **Roofing Distributor (our client)** → Roofing Contractors (the leads)

The platform scrapes public contractor data from GAF's directory, enriches it with AI-generated sales insights, and presents it in a polished dashboard for sales reps to use during account planning.

---

## Data Source

- **URL:** https://www.gaf.com/en-us/roofing-contractors/residential?distance=25
- **ZIP Code:** 10013 (Manhattan, NY)
- **Scope:** Residential roofing contractors within 25-mile radius
- **Expected data per contractor:**
  - Company name
  - Address / location
  - Phone number
  - Website URL
  - GAF certification level (Master Elite, Certified, etc.)
  - Star rating and review count
  - Services offered
  - Years in business / other profile details

---

## What the Platform Must Do

1. **Scrape** contractor data from GAF's public directory for the given ZIP code and radius
2. **Store** that data in a structured, queryable way suitable for production
3. **Enrich** each contractor record with AI-generated sales intelligence:
   - Lead score (priority ranking)
   - Talking points for sales reps
   - Business insights and upsell opportunities
   - Recommended next actions
4. **Display** leads in an intuitive UI where sales reps can browse, filter, sort, and drill into individual leads

---

## Evaluation Criteria (from the brief)

### 1. Intuitive UI
- There must be a way for reps to view the leads the system generates
- Bonus for: visual polish, clear information presentation, distinctive or creative features

### 2. Robust Data Management
- Solution needs a way to store, organize, and retrieve data
- Approach should be suitable for a production environment
- Acceptable to outline future improvements given the time constraint

### 3. Scalable Pipeline
- Pipeline should be designed with scale in mind (eventually hundreds/thousands of reps)
- Clear, well-structured code and sound engineering practices
- Important for maintainability, collaboration, and minimizing technical debt

---

## Time Constraint

3-4 hours total. A working demo with real data should be the priority by the halfway mark. Polish and documentation fill the remaining time.

---

## Key Domain Knowledge

- **GAF certification tiers** matter for lead scoring — Master Elite is the highest tier (top 2% of contractors), then Certified, then uncertified. Higher-tier contractors do more volume and buy more premium products.
- **Review count and rating** are proxies for business volume — a contractor with 100+ reviews is busier (and buys more materials) than one with 5 reviews.
- **Services offered** signal product needs — a contractor doing both residential and commercial work needs a broader product range.
- **Proximity** to the distributor's warehouse/territory matters for logistics and relationship building.
- Sales reps use this data during **account planning** — they need actionable insights, not raw data dumps.
