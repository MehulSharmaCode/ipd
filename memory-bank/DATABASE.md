# DATABASE.md — AgriSense Database Schema
> **Last Updated:** 2026-07-21 | Cross-reference: ARCHITECTURE.md, API_REFERENCE.md

---

## Overview

- **Engine:** MongoDB (local, no authentication)
- **Database Name:** `agrisense_db`
- **Driver:** Motor 3.3.2 (async) + PyMongo 4.6.2
- **Connection:** `mongodb://127.0.0.1:27017` (configured via `.env`)
- **Timeout:** 5000ms server selection timeout

---

## Collections

### 1. `farmers`

The primary collection. Stores farmer accounts, profiles, and document verification status.

#### Schema

```json
{
  "_id": "ObjectId (auto-generated)",

  // --- Account fields (created at signup) ---
  "full_name": "string",
  "email": "string (normalized lowercase, UNIQUE)",
  "hashed_password": "string (bcrypt hash)",

  // --- Profile fields (filled in ProfileWizard) ---
  "phone_number": "string | null",
  "age": "int (≥18) | null",
  "gender": "string ('Male'|'Female'|'Other') | null",
  "category": "string ('General'|'OBC'|'SC'|'ST') | null",
  "is_differently_abled": "boolean (default: false)",
  "highest_qualification": "string | null",

  // --- Location ---
  "state": "string | null",
  "district": "string | null",
  "pincode": "string | null",

  // --- Identity & Financial ---
  "is_verified": "boolean (default: false)",
  "aadhar_number": "string (12 digits, no spaces) | null",
  "pan_number": "string (AAAAA9999A format) | null",
  "is_aadhar_verified": "boolean (default: false)",
  "is_pan_verified": "boolean (default: false)",
  "annual_income": "float | null",
  "bank_account_linked": "boolean (default: false)",

  // --- Agricultural Data ---
  "land_size_hectares": "float | null",
  "farmer_type": "string ('Small'|'Medium'|'Large') | null",
  "irrigation_type": "string ('Rainfed'|'Canal'|'Well'|'Drip'|'Sprinkler') | null",
  "soil_type": "string ('Alluvial'|'Black'|'Red'|'Laterite'|'Desert'|'Mountain') | null",
  "crop_season": "string ('Kharif'|'Rabi'|'Zaid') | null",
  "water_source": "string | null",
  "land_ownership": "string ('Owned'|'Leased'|'Shared') | null",
  "primary_crops": "array[string] (default: [])",
  "preferred_language": "string ('en'|'hi'|'mr'|'gu', default: 'en')",

  // --- ML-specific fields ---
  "crop": "string | null",
  "temperature": "float | null",
  "rainfall": "float | null",
  "soil": "string | null",
  "season": "string | null",

  // --- Metadata ---
  "documents_uploaded": "array[string] (format: 'doctype:filepath')",
  "profile_wizard_complete": "boolean (default: false)"
}
```

#### Notes
- `_id` is a MongoDB ObjectId, returned as string in API responses
- `email` is always stored normalized to lowercase
- `hashed_password` is NEVER returned in API responses (not in FarmerResponse model)
- `recommended_schemes`, `recommended_bundles`, `ineligible_schemes`, `predictive_alerts` are **computed at runtime** — NOT stored in MongoDB
- `aadhar_number` is validated: exactly 12 digits, first digit ≠ 0 or 1
- `pan_number` is validated: regex `^[A-Z]{5}[0-9]{4}[A-Z]$`
- `documents_uploaded` stores strings like `"aadhar:uploads/abc.jpg"`, `"pan:uploads/def.png"`

#### Indexes
- **No explicit indexes defined** in code (MongoDB auto-indexes `_id`)
- **Recommended to add:** unique index on `email` field (currently only checked via `find_one` at signup)

#### Access Pattern
```python
# Connection
db = get_db()  # returns AsyncIOMotorDatabase

# Common operations
db["farmers"].find_one({"email": email})
db["farmers"].find_one({"_id": ObjectId(farmer_id)})
db["farmers"].insert_one(farmer_dict)
db["farmers"].update_one({"_id": ObjectId(id)}, {"$set": update_data})
db["farmers"].update_one({"_id": ObjectId(id)}, {"$addToSet": {"documents_uploaded": record}})
db["farmers"].find({})  # list all
```

---

### 2. `stories`

Community success stories posted by farmers.

#### Schema

```json
{
  "_id": "ObjectId (auto-generated)",

  // --- Content ---
  "title": "string (required)",
  "content": "string (required, full text)",
  "crop_type": "string | null",
  "location_state": "string | null",
  "location_district": "string | null",
  "scheme_id": "string | null (e.g., 'PM_KISAN')",
  "media_url": "string (HTTP URL) | null",
  "tags": "array[string] (default: [])",

  // --- Author (denormalized) ---
  "farmer_id": "string (ObjectId as string, references farmers._id)",
  "farmer_name": "string (denormalized from farmer record at time of creation)",

  // --- Engagement ---
  "upvotes": "int (default: 0)",
  "upvoted_by": "array[string] (farmer_id strings of upvoters)",

  // --- Timestamps ---
  "created_at": "datetime (UTC, auto-set)",
  "updated_at": "datetime (UTC, auto-set)"
}
```

#### Notes
- `farmer_id` is a string reference (not a real ObjectId reference) — no foreign key enforcement
- `farmer_name` is denormalized (copied at creation time) for read performance
- `upvoted_by` enables idempotent toggle upvote without double-counting
- Upvote toggle: add farmer_id to `upvoted_by` + increment `upvotes`, or remove + decrement
- No soft delete or moderation system exists yet

#### Access Pattern
```python
db.stories.insert_one(story_dict)
db.stories.find(query).sort("created_at", -1).skip(skip).limit(limit)
db.stories.find().sort("upvotes", -1).limit(3)
db.stories.find_one({"_id": ObjectId(story_id)})
db.stories.update_one({"_id": obj_id}, {"$inc": {"upvotes": 1}, "$push": {"upvoted_by": farmer_id}})
db.stories.update_one({"_id": obj_id}, {"$inc": {"upvotes": -1}, "$pull": {"upvoted_by": farmer_id}})
```

---

## Relationships

```
farmers._id (string) ──referenced by──► stories.farmer_id (string)
```
- **Type:** Denormalized reference (one-to-many: one farmer, many stories)
- **No enforced referential integrity** — MongoDB document model
- **No cascade delete** — stories remain if farmer is deleted (no delete endpoint exists anyway)

---

## Validation Summary

### At Model Level (Pydantic)
| Field | Validator | Rule |
|---|---|---|
| `aadhar_number` | `@field_validator` | Exactly 12 digits (after removing spaces), no leading 0 or 1 |
| `pan_number` | `@field_validator` | Regex `^[A-Z]{5}[0-9]{4}[A-Z]$` (uppercase enforced) |
| `email` | Pydantic `EmailStr` | RFC 5322 email format |
| `age` | Pydantic `Field(ge=18)` | Must be ≥ 18 |

### At API Level
| Field | Check |
|---|---|
| `email` | Unique check via `find_one` before `insert_one` |
| Aadhaar OCR number | First digit ≠ 0 or 1 (UIDAI spec) |
| DOB | Year in range 1900–2024 |

---

## Environment Configuration

```bash
# backend/.env
MONGO_URI=mongodb://127.0.0.1:27017
DATABASE_NAME=agrisense_db
SECRET_KEY=my_super_secret_hackathon_key_123  # ← CHANGE IN PRODUCTION
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## Known Issues / Missing Items

1. **No unique index on `farmers.email`** — uniqueness enforced by application logic only (`find_one` + `insert_one`). Should add a MongoDB index for data integrity.
2. **No indexes on `stories`** — `upvotes` and `created_at` queries lack indexes. Should add for performance at scale.
3. **`farmer_id` in stories is a string, not ObjectId** — prevents proper join queries if needed later.
4. **No TTL indexes** — uploaded documents in `documents_uploaded` array accumulate indefinitely.
5. **No schema versioning** — no migration system; schema is implicit via Pydantic models.
6. **Computed fields not stored** — `recommended_schemes`, `predictive_alerts` are recomputed on every GET, which is computationally expensive. Could be cached.
