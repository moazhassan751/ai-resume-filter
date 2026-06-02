"""Inventory all datasets in the project."""
import os
import json
from pathlib import Path
import pandas as pd


def main():
    base_path = Path(".")
    
    print("=" * 80)
    print("DATASET INVENTORY")
    print("=" * 80)
    
    # 1. Resume PDFs by category
    data_dir = base_path / "data" / "data"
    if data_dir.exists():
        print("\n1. RESUME PDFs BY CATEGORY (data/data/)")
        print("-" * 80)
        categories = {}
        for category_dir in sorted(data_dir.iterdir()):
            if category_dir.is_dir():
                pdf_count = len(list(category_dir.glob("*.pdf")))
                categories[category_dir.name] = pdf_count
                print(f"  {category_dir.name}: {pdf_count} PDFs")
        print(f"Total categories: {len(categories)}")
        print(f"Total PDFs: {sum(categories.values())}")
    
    # 2. CareerCorpus
    career_corpus = base_path / "CareerCorpus  A Comprehensive Dataset of Annotated" / "CareerCorpus.xlsx"
    if career_corpus.exists():
        print("\n2. CAREER CORPUS (CareerCorpus.xlsx)")
        print("-" * 80)
        try:
            df = pd.read_excel(career_corpus)
            print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Sample row 0:")
            for col in df.columns:
                val = str(df[col].iloc[0])[:80]
                print(f"    {col}: {val}")
        except Exception as e:
            print(f"  Error reading: {e}")
    
    # 3. Resume.csv
    resume_csv = base_path / "Resume" / "Resume.csv"
    if resume_csv.exists():
        print("\n3. RESUME CSV (Resume/Resume.csv)")
        print("-" * 80)
        try:
            df = pd.read_csv(resume_csv)
            print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns")
            print(f"  Columns: {list(df.columns)}")
        except Exception as e:
            print(f"  Error reading: {e}")
    
    # 4. resume_data.csv
    resume_data_csv = base_path / "resume_data.csv"
    if resume_data_csv.exists():
        print("\n4. RESUME DATA CSV (resume_data.csv)")
        print("-" * 80)
        try:
            df = pd.read_csv(resume_data_csv)
            print(f"  Shape: {df.shape[0]} rows x {df.shape[1]} columns")
            print(f"  Columns: {list(df.columns)[:10]}... ({len(df.columns)} total)")
        except Exception as e:
            print(f"  Error reading: {e}")
    
    # 5. resumes_dataset.jsonl
    jsonl_file = base_path / "resumes_dataset.jsonl"
    if jsonl_file.exists():
        print("\n5. RESUMES DATASET JSONL (resumes_dataset.jsonl)")
        print("-" * 80)
        try:
            with open(jsonl_file) as f:
                lines = f.readlines()
            print(f"  Total records: {len(lines)}")
            if lines:
                first = json.loads(lines[0])
                print(f"  Keys in first record: {list(first.keys())}")
        except Exception as e:
            print(f"  Error reading: {e}")
    
    # 6. ResumeAtlas (Hugging Face)
    print("\n6. RESUME ATLAS (Hugging Face)")
    print("-" * 80)
    print("  Dataset: ahmedheakl/resume-atlas")
    print("  Source: Hugging Face datasets")
    print("  Split: train (13,389 examples)")
    print("  Features: Category (job title), Text (cleaned resume)")
    print("  Ready to download on demand")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
