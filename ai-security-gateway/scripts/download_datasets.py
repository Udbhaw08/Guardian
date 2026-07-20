"""
scripts/download_datasets.py
-----------------------------
Downloads and merges prompt injection datasets from HuggingFace.

Improvements over v1:
- Deduplication: removes exact-duplicate 'text' rows
- Label conflict detection: removes same text appearing with different labels
- Expanded synthetic safe examples covering FP-triggering patterns:
    * Educational prompts using "no restrictions" in context
    * Code/programming with words like override, ignore, instructions
    * Conversational Q&A with injection-surface vocabulary
    * Document/invoice text
- Class imbalance reporting
"""

import os

import pandas as pd
from datasets import load_dataset


# ── Safe example generators ────────────────────────────────────────────────────

def generate_safe_financial_text() -> list[str]:
    """Safe (label=0) financial/invoice text to prevent false positives."""
    return [
        "What is the total amount due on this invoice?",
        "Total Due INR 3,42,200",
        "Bank: HDFC Bank A/C: 0012849372 IFSC: HDFC0001284",
        "Payment due within 14 days.",
        "Goods Services Tax GSTIN 07AADCN4928L1ZV",
        "Permanent Account Number PAN AADCN4928L",
        "1. All invoices must be reviewed against the purchase order before processing.",
        "2. Retain a copy of this document in the accounts receivable register for audit purposes.",
        "3. Any discrepancies in line items or totals must be escalated to the finance controller.",
        "5. GST amounts are computed per the rate applicable at the invoice date.",
        "6. Payments processed after the due date will incur a late fee as stated above.",
        "7. Original copies must be maintained for a minimum of 7 financial years.",
        "Legal Disclaimer",
        "This invoice and its contents are confidential and intended solely for the named recipient.",
        "Web Application Development (Phase 2) 1 project 1,80,000",
        "Cloud Infrastructure Setup (AWS) 1 setup 45,000",
        "Security Auditing Penetration Test 1 project 50,000",
        "Content Delivery Network Setup 1 setup 15,000",
        "Subtotal 2,90,000",
        "GST 18% 52,200",
        "Invoice Number: INV-2023-001",
        "Please remit payment to the account listed below.",
        "If you have any questions regarding this invoice, please contact our billing department.",
        "Late payments may be subject to a 1.5% monthly interest charge.",
        "Thank you for your business.",
        "Total Payable: $1,250.00",
        "Amount Paid: $0.00",
        "Balance Due: $1,250.00",
        "Please include the invoice number on your check.",
        "Wire transfer details:",
        "SWIFT Code: CHASEUS33",
        "Routing Number: 122000248",
        "Account Holder: ACME Corp",
        "Tax ID: 12-3456789",
        "Item Description Qty Unit Price Total",
        "Consulting Services 10 hrs $150.00 $1,500.00",
        "Software License (Annual) 1 $500.00 $500.00",
        "Hardware Maintenance 1 $200.00 $200.00",
        "Shipping & Handling 1 $50.00 $50.00",
        "Total: $2,250.00",
        "Payment Terms: Net 30",
        "Due Date: 12/31/2023",
        "Invoice Date: 12/01/2023",
        "Bill To: John Doe",
        "Ship To: Jane Doe",
        "Company: XYZ Inc.",
        "Address: 123 Main St, Anytown, USA",
        "Phone: 555-123-4567",
        "Email: billing@xyz.com",
        # Invoice lines that use "ignore", "disregard" in financial context
        "Disregard the tax line — it will be computed automatically by the system.",
        "Please ignore the draft watermark on this invoice copy.",
        "Note: ignore line items marked with an asterisk until confirmed by procurement.",
        "Prior instructions from the finance team: hold payment until PO is matched.",
    ]


def generate_safe_conversational_text() -> list[str]:
    """
    Safe (label=0) conversational prompts that contain injection-surface words
    but are clearly legitimate user requests.

    These are the kinds of prompts that cause false positives in the current model.
    """
    return [
        # Educational/DSA — uses "no restrictions", "pretend", roleplay framing
        "pretend as a teacher and you have no restrictions in explaining two pointer approach in dsa",
        "act as an experienced professor and explain dynamic programming to me with examples",
        "pretend you are a senior engineer explaining system design concepts with no time restrictions",
        "you have no restrictions in explaining recursion to me — I am a beginner",
        "act as a coding mentor and help me understand binary search algorithm step by step",
        "pretend there are no restrictions on explanation length and walk me through quicksort",
        "assume you are a patient teacher with no topic restrictions and explain graph traversal",

        # Programming — uses "override", "ignore", "instructions", "system"
        "How do I override a base class method in Python?",
        "Can you explain method overriding with an example in Java?",
        "override the default configuration value in this YAML file — how do I do that?",
        "I need to override the parent class constructor. Is super().__init__() the right approach?",
        "What does it mean to override an abstract method in Python?",
        "ignore this compiler error and explain what causes it: IndexError list index out of range",
        "What should I ignore in this error log? It shows warnings but the app still runs.",
        "How do I set a system prompt for my chatbot application?",
        "explain what a system prompt is and how it affects LLM behaviour",
        "I want to write a system-level configuration file. What format should I use?",
        "How do I write instructions in a config file that the program will follow?",
        "my code has a class that overrides the render() method — is this good design?",
        "What is instruction tuning in the context of large language models?",
        "How do prior instructions affect the output of a transformer model?",
        "Can you explain what previous context means in a multi-turn conversation?",
        "ignore all whitespace in this regex pattern: [\\s\\t\\n]+",
        "The system is not responding. What should I check first?",
        "How do I bypass the login page in my own app during local testing?",
        "I want to bypass the rate limiter for my internal test environment.",
        "How do I get around the CORS restriction in my local dev setup?",

        # Creative writing — uses "no restrictions", "pretend", "act as"
        "write a short story where the character has no restrictions on their imagination",
        "help me write a scene where the protagonist pretends to be someone else entirely",
        "for this creative writing exercise you have no restrictions on genre or style",
        "act as a creative collaborator and help me brainstorm plot ideas with no limits",
        "pretend you are narrating an adventure story with no word count restrictions",

        # General Q&A
        "What is the capital of France?",
        "Could you help me understand the difference between a list and a tuple in Python?",
        "How does gradient descent work in machine learning?",
        "Can you summarize this article for me?",
        "What are some good books on system design?",
        "How do transformers work in NLP?",
        "Explain attention mechanism in simple terms.",
        "What is the time complexity of merge sort?",
        "How do I connect to a PostgreSQL database in Python?",
        "What is the difference between REST and GraphQL?",
        "Help me write a cover letter for a software engineering position.",
        "Can you review this Python function and suggest improvements?",
        "What are best practices for writing unit tests?",
        "Explain SOLID principles in software engineering.",
        "How do I set up a virtual environment in Python?",

        # Tech support
        "My application is throwing a 500 error — how do I debug it?",
        "The server is not starting. The logs say 'address already in use'.",
        "How do I configure environment variables for a Docker container?",
        "What does 'permission denied' mean in Linux and how do I fix it?",
        "My React component is not re-rendering. What could be the issue?",

        # Requests with ambiguous phrasing
        "please ignore the extra spaces in this document and process it normally",
        "I want you to act as a grammar checker — no restrictions on correction style",
        "can you act as a proofreader and give me feedback with no restrictions?",
        "my boss instructed me to disregard these ESLint warnings — is that safe?",
        "Prior instructions in section 3 say to disregard the tax entry. Is this invoice correct?",
        "The documentation says to ignore this flag during initial setup.",
        "act as if you are explaining this to a 5-year-old and simplify your language",
    ]


def generate_safe_coding_text() -> list[str]:
    """Safe code snippets and technical text that might trigger false positives."""
    return [
        "def override_config(base, override): return {**base, **override}",
        "class MyModel(BaseModel): def predict(self, x): return super().predict(x)",
        "# Ignore type: ignore comments are used to suppress mypy errors",
        "Instructions: Run pytest with --ignore=tests/integration to skip integration tests.",
        "Step 1: Override the default port in config.yaml",
        "Step 2: Set system environment variables as per the deployment instructions",
        "Step 3: Ignore the SSL warning if using a self-signed certificate in development",
        "git config --global core.ignorecase false",
        "# This function bypasses the cache for fresh data retrieval",
        "How to bypass SSL verification in requests: verify=False (dev only!)",
        "# Override parent class method to add logging",
    ]


# ── Main pipeline ──────────────────────────────────────────────────────────────

def main():
    print("Downloading and merging datasets from HuggingFace...")
    all_data: list[pd.DataFrame] = []

    # 1. neuralchemy/prompt-injection-Threat-Matrix (binary)
    try:
        print("  Loading neuralchemy/prompt-injection-Threat-Matrix (binary)...")
        ds1 = load_dataset("neuralchemy/prompt-injection-Threat-Matrix", "binary")
        df1 = ds1["train"].to_pandas()
        if "text" in df1.columns and "label" in df1.columns:
            all_data.append(df1[["text", "label"]])
            print(f"    [OK] Loaded {len(df1)} rows")
        else:
            print(f"    Missing expected columns. Found: {list(df1.columns)}")
    except Exception as e:
        print(f"  Failed to load neuralchemy dataset: {e}")

    # 2. S-Labs/prompt-injection-dataset
    try:
        print("  Loading S-Labs/prompt-injection-dataset...")
        ds2 = load_dataset("S-Labs/prompt-injection-dataset")
        df2 = ds2["train"].to_pandas()
        if "text" in df2.columns and "label" in df2.columns:
            all_data.append(df2[["text", "label"]])
            print(f"    [OK] Loaded {len(df2)} rows")
        else:
            print(f"    Missing expected columns. Found: {list(df2.columns)}")
    except Exception as e:
        print(f"  Failed to load S-Labs dataset: {e}")

    # 3. Mukta9904/Financial-Prompt-Injection-Dataset
    try:
        print("  Loading Mukta9904/Financial-Prompt-Injection-Dataset...")
        # Specify data_files to bypass the broken test.csv in the repo
        ds3 = load_dataset("Mukta9904/Financial-Prompt-Injection-Dataset", data_files="train.csv", split="train")
        df3 = ds3.to_pandas()
        if "prompt" in df3.columns and "label" in df3.columns:
            df3 = df3.rename(columns={"prompt": "text"})
        if "text" in df3.columns and "label" in df3.columns:
            all_data.append(df3[["text", "label"]])
            print(f"    [OK] Loaded {len(df3)} rows")
        else:
            print(f"    Missing expected columns. Found: {list(df3.columns)}")
    except Exception as e:
        print(f"  Failed to load Mukta9904 dataset: {e}")

    # 4. Existing train.csv
    existing_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "train.csv")
    if os.path.exists(existing_path):
        print(f"  Loading existing dataset: {existing_path}...")
        df_exist = pd.read_csv(existing_path)
        if "text" in df_exist.columns and "label" in df_exist.columns:
            all_data.append(df_exist[["text", "label"]])
            print(f"    [OK] Loaded {len(df_exist)} rows")
        else:
            print("    Missing 'text' or 'label' columns in existing train.csv")

    # 5. Synthetic safe examples (financial, conversational, coding)
    print("  Adding synthetic safe examples...")
    safe_texts = (
        generate_safe_financial_text()
        + generate_safe_conversational_text()
        + generate_safe_coding_text()
    )
    df_safe = pd.DataFrame({"text": safe_texts, "label": [0] * len(safe_texts)})
    all_data.append(df_safe)
    print(f"    [OK] Added {len(safe_texts)} synthetic safe examples")

    # ── Combine ────────────────────────────────────────────────────────────────
    if not all_data:
        print("No data collected!")
        return

    merged_df = pd.concat(all_data, ignore_index=True)

    # ── Clean ──────────────────────────────────────────────────────────────────
    before_clean = len(merged_df)
    merged_df = merged_df.dropna(subset=["text", "label"])
    merged_df["text"] = merged_df["text"].astype(str).str.strip()
    merged_df["label"] = merged_df["label"].astype(int)
    merged_df = merged_df[merged_df["text"] != ""]
    print(f"\nCleaning: {before_clean} -> {len(merged_df)} rows (removed {before_clean - len(merged_df)} empty/null)")

    # ── Deduplicate ────────────────────────────────────────────────────────────
    before_dedup = len(merged_df)
    # First: detect label conflicts (same text, different labels across datasets)
    label_counts = merged_df.groupby("text")["label"].nunique()
    conflicted_texts = label_counts[label_counts > 1].index
    if len(conflicted_texts) > 0:
        print(f"Label conflicts detected: {len(conflicted_texts)} texts have conflicting labels across datasets -> removed")
        merged_df = merged_df[~merged_df["text"].isin(conflicted_texts)]

    # Then: drop exact duplicates (same text, same label)
    merged_df = merged_df.drop_duplicates(subset=["text"])
    print(f"Deduplication: {before_dedup} -> {len(merged_df)} rows (removed {before_dedup - len(merged_df)} duplicates/conflicts)")

    # ── Class balance report ──────────────────────────────────────────────────
    n_safe = (merged_df["label"] == 0).sum()
    n_inj  = (merged_df["label"] == 1).sum()
    ratio  = n_inj / len(merged_df) * 100
    print(f"\nClass distribution:")
    print(f"  Safe prompts  (0): {n_safe}")
    print(f"  Injections    (1): {n_inj}")
    print(f"  Injection ratio:   {ratio:.1f}%")
    if ratio > 75:
        print("  [WARN] Injection class is dominant (>75%). class_weight='balanced' in train.py will compensate.")
    elif ratio < 25:
        print("  [WARN] Safe class is dominant (<25% injections). class_weight='balanced' in train.py will compensate.")
    else:
        print("  [OK] Class balance is reasonable.")

    # ── Shuffle and save ──────────────────────────────────────────────────────
    merged_df = merged_df.sample(frac=1, random_state=42).reset_index(drop=True)

    out_dir = os.path.join(os.path.dirname(__file__), "..", "datasets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "merged_train.csv")
    merged_df.to_csv(out_path, index=False)

    print(f"\n[OK] Merged dataset saved -> {out_path}")
    print(f"   Total rows: {len(merged_df)}")


if __name__ == "__main__":
    main()
