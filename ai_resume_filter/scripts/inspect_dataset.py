"""Inspect the resume-atlas dataset from Hugging Face."""
from datasets import load_dataset
import json


def main():
    print("Loading resume-atlas dataset...")
    try:
        ds = load_dataset("ahmedheakl/resume-atlas")
        print(f"Dataset keys: {ds.keys()}")
        
        for split_name, split_data in ds.items():
            print(f"\n=== Split: {split_name} ===")
            print(f"Number of examples: {len(split_data)}")
            print(f"Features: {split_data.features.keys()}")
            
            if len(split_data) > 0:
                example = split_data[0]
                print(f"\nFirst example:")
                for key, val in example.items():
                    if isinstance(val, str):
                        preview = val[:100] + "..." if len(val) > 100 else val
                    else:
                        preview = str(val)[:100]
                    print(f"  {key}: {preview}")
                
                # Print full first example as JSON
                print(f"\nFull first example (JSON):")
                print(json.dumps(example, indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
