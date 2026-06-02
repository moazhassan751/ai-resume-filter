# 📊 AI Resume Filter - Complete Dataset Inventory

## Overview
You have **6 major data sources** totaling **~145 MB** with **28,814 total resumes/records** across multiple formats.

---

## Dataset Breakdown

### 1. 📄 **resume_data.csv** - Highly Structured Resume Data
- **Location**: `d:\ai-resume-filter\resume_data.csv`
- **Format**: CSV (69.8 MB)
- **Rows**: 9,544 unique resumes
- **Columns**: 35 fields (highly parsed)
- **Key Fields**:
  - `career_objective` - Job seekers' goals
  - `skills` - Technical and soft skills (list format)
  - `educational_institution_name` - University/School
  - `degree_names` - Degrees (Bachelor, Master, etc.)
  - `professional_company_names` - Past employers
  - `positions` - Job titles held
  - `responsibilities` - Role descriptions
  - `languages` - Languages spoken
  - `certification_skills` - Certifications
  - `matched_score` - Pre-computed match score
- **Best For**: Feature extraction, job title classification, skill analysis
- **Quality**: **EXCELLENT** - Pre-parsed, structured, ready for ML

---

### 2. 📋 **Resume/Resume.csv** - Raw Resume + Category Labels
- **Location**: `d:\ai-resume-filter\Resume\Resume.csv`
- **Format**: CSV (variable size)
- **Rows**: 2,484 resumes
- **Columns**: 4
  - `ID` - Unique identifier
  - `Resume_str` - Plain text resume
  - `Resume_html` - HTML formatted resume
  - `Category` - Job category label (24 categories)
- **Best For**: Text classification, NLP model training, category prediction
- **Quality**: **GOOD** - Raw text + labels, needs text preprocessing

---

### 3. 📦 **resumes_dataset.jsonl** - Structured JSON Records
- **Location**: `d:\ai-resume-filter\resumes_dataset.jsonl`
- **Format**: JSONL (16.3 MB)
- **Records**: 3,500 resumes
- **Keys**: 12 structured fields
  - `ResumeID`, `Category`, `Name`, `Email`, `Phone`, `Location`
  - `Summary` - Professional summary
  - `Skills` - Structured skill list
  - `Experience` - Work history
  - `Education` - Educational background
  - `Text` - Full resume text
  - `Source` - Data source
- **Best For**: Entity extraction, semantic search, RAG, comprehensive NLP tasks
- **Quality**: **EXCELLENT** - Rich structure, clean JSON format

---

### 4. 📁 **PDF Resume Files** - Raw Documents by Category
- **Location**: `d:\ai-resume-filter\data\data\<CATEGORY>\*.pdf`
- **Format**: PDF files
- **Structure**: 24 job categories, ~100-120 PDFs per category
- **Total Files**: 2,484 PDFs
- **Categories**: (alphabetically)
  - ACCOUNTANT, ADVOCATE, AGRICULTURE, APPAREL, ARTS, AUTOMOBILE, AVIATION
  - BANKING, BPO, BUSINESS-DEVELOPMENT, CHEF, CONSTRUCTION, CONSULTANT
  - DESIGNER, DIGITAL-MEDIA, ENGINEERING, FINANCE, FITNESS
  - HEALTHCARE, HR, INFORMATION-TECHNOLOGY, PUBLIC-RELATIONS, SALES, TEACHER
- **Top 5 Categories**:
  - BUSINESS-DEVELOPMENT: 120
  - INFORMATION-TECHNOLOGY: 120
  - ACCOUNTANT: 118
  - ADVOCATE: 118
  - CHEF: 118
- **Best For**: PDF parsing, OCR, document processing, multimodal models
- **Quality**: **NEEDS WORK** - Requires PDF → text conversion (pypdf, pdfplumber, or OCR)

---

### 5. 🎓 **CareerCorpus.xlsx** - Annotated Career Data
- **Location**: `d:\ai-resume-filter\CareerCorpus  A Comprehensive Dataset of Annotated\CareerCorpus.xlsx`
- **Format**: Excel
- **Rows**: 302 annotated records
- **Columns**: 8
  - `ID` - Record ID
  - `Domain` - Career domain
  - `Education` - Education details
  - `Skills and Achievements` - Skill annotations
  - `Experience` - Experience details
  - `Job_type` - Job classification
  - `Annotator-1`, `Annotator-2` - Multiple annotator labels
- **Best For**: Inter-annotator agreement analysis, quality control, domain classification
- **Quality**: **GOOD** - Small but high-quality annotated dataset

---

### 6. 🤗 **resume-atlas (HuggingFace)** - Pre-trained Dataset
- **Source**: `ahmedheakl/resume-atlas` from HuggingFace
- **Format**: Dataset with train/test splits
- **Records**: 13,389 labeled examples (train split)
- **Columns**: 2
  - `Category` - Job title/category (23 unique categories)
  - `Text` - Preprocessed resume text
- **Best For**: Transfer learning, multi-dataset ensemble training
- **Quality**: **EXCELLENT** - Large, clean, preprocessed, ready for ML
- **How to Load**:
  ```python
  from datasets import load_dataset
  dataset = load_dataset('ahmedheakl/resume-atlas', split='train')
  ```

---

## 🎯 Data Strategy by Use Case

### Scenario 1: **Resume Classification (Predict Job Category)**
**Primary**: Resume.csv (#2) + resume-atlas (#6)
**Secondary**: resume_data.csv (#1), resumes_dataset.jsonl (#3)
- Use `Resume.csv` + `resume-atlas` as training data
- Resume text → Category prediction

### Scenario 2: **Resume Parsing & Information Extraction**
**Primary**: resume_data.csv (#1), resumes_dataset.jsonl (#3)
**Secondary**: Resume PDFs (#4)
- Extract skills, education, experience, responsibilities
- Use as training labels for NER/entity extraction models

### Scenario 3: **Skill Matching & Resume Scoring**
**Primary**: resume_data.csv (#1) - has pre-parsed skills
**Secondary**: resume_data.csv has `matched_score` column
- Direct use for ML model training

### Scenario 4: **Semantic Search & RAG**
**Primary**: resumes_dataset.jsonl (#3) + Resume.csv (#2)
**Secondary**: resume-atlas (#6)
- Vectorize text, build embeddings index
- Query matching against skill requirements

### Scenario 5: **Quality Assurance & Annotation**
**Primary**: CareerCorpus.xlsx (#5) + resume_data.csv (#1)
- Small curated dataset for validation
- Check model predictions against gold-standard annotations

---

## 💾 Total Data Size Summary

| Dataset | Format | Size | Records | Status |
|---------|--------|------|---------|--------|
| resume_data.csv | CSV | 69.8 MB | 9,544 | ✅ Ready |
| Resume/Resume.csv | CSV | ~5 MB | 2,484 | ✅ Ready |
| resumes_dataset.jsonl | JSONL | 16.3 MB | 3,500 | ✅ Ready |
| PDF Resumes | PDF | 59.1 MB | 2,484 | ⚠️ Needs OCR |
| CareerCorpus.xlsx | Excel | 0.1 MB | 302 | ✅ Ready |
| resume-atlas (HF) | Dataset | ~30 MB | 13,389 | ✅ On-demand |
| **TOTAL** | **Mixed** | **~180 MB** | **~31,703** | **Ready to use** |

---

## 🔄 Recommended Data Pipeline

### Step 1: Load Core Datasets (Fast)
```python
from services.data_loader import DataPipeline

pipeline = DataPipeline()
# Load local CSVs, JSONL, Excel
pipeline.load_all_datasets(skip_hf=True)

stats = pipeline.get_dataset_stats()
print(stats)  # Preview all datasets
```

### Step 2: Normalize & Standardize
Create unified schema for all datasets:
```python
{
    "id": str,
    "text": str,              # Full resume text
    "category": str,          # Job category label
    "skills": List[str],      # Extracted skills
    "education": str,         # Educational background
    "experience": str,        # Work experience
    "source": str,           # Which dataset it came from
}
```

### Step 3: Create Training Splits
- **Training** (70%): resume-atlas + resume_data.csv
- **Validation** (15%): Resume.csv
- **Test** (15%): CareerCorpus (gold standard)

### Step 4: Build ML Models
1. **Classification**: Resume Category Prediction
2. **Extraction**: Skill/Education/Experience NER
3. **Matching**: Similarity scoring

---

## 🤖 Next Steps for CrewAI Integration

### Agent 1: **Resume Loader Agent**
- Reads from all 6 data sources
- Normalizes to unified schema
- Outputs: Standardized dataset

### Agent 2: **Resume Parser Agent**
- Extracts structure from raw text
- Produces: Skills, Education, Experience, Certifications
- Training data from: resume_data.csv (#1)

### Agent 3: **Category Classifier Agent**
- Predicts job category from resume text
- Training data: resume-atlas (#6) + Resume.csv (#2)
- Output: Predicted category + confidence

### Agent 4: **Skills Matcher Agent**
- Matches candidate skills against job requirements
- Uses parsed data from Agent 2
- Training data: resume_data.csv matched_score column

### Orchestrator Workflow
```
User Upload → Resume Loader → Parser → Classifier → Skills Matcher → Report
```

---

## 🚀 Quick Start Commands

### View all datasets
```bash
cd ai_resume_filter
python services/data_loader.py
```

### Load and explore specific dataset
```python
from services.data_loader import DataLoader
loader = DataLoader(base_path="../..")

# Load CSV
df = loader.load_csv("resume_data.csv")
print(f"Rows: {len(df)}, Skills sample: {df['skills'].iloc[0]}")

# Load JSONL
records = loader.load_jsonl("resumes_dataset.jsonl")
print(f"Records: {len(records)}, First: {records[0]}")

# Load from HuggingFace
hf_data, cols = loader.load_huggingface("ahmedheakl/resume-atlas")
print(f"HF Examples: {len(hf_data)}, Features: {cols}")
```

---

## 📝 Notes

- **PDF Extraction**: Will need `pypdf` or `pdfplumber` + possibly `pytesseract` for OCR
- **Data Caching**: Consider caching loaded CSVs/JSONL locally for faster access
- **Incremental Loading**: For large datasets, use streaming/chunking to avoid memory issues
- **Data Quality**: resume_data.csv and resumes_dataset.jsonl are highest quality
- **Resume Atlas**: Best for transfer learning - highly curated, preprocessed data

---

## 📦 Update requirements.txt

Add these for data loading:
```
datasets>=2.16.0  # HuggingFace datasets
openpyxl>=3.10.0  # Excel support
pdfplumber>=0.10.0  # PDF extraction (alternative to pypdf)
pymupdf==1.24.1   # Fast PDF reading
```

