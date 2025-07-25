import json
import re
import io
from typing import Dict, Set, Any

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Helper utilities
# ----------------------------------------------------------------------------

def get_default_dictionaries() -> Dict[str, Set[str]]:
    """Return the default keyword dictionaries."""
    return {
        "urgency_marketing": {
            "limited", "limited time", "limited run", "limited edition", "order now",
            "last chance", "hurry", "while supplies last", "before they're gone",
            "selling out", "selling fast", "act now", "don't wait", "today only",
            "expires soon", "final hours", "almost gone",
        },
        "exclusive_marketing": {
            "exclusive", "exclusively", "exclusive offer", "exclusive deal",
            "members only", "vip", "special access", "invitation only",
            "premium", "privileged", "limited access", "select customers",
            "insider", "private sale", "early access",
        },
    }

_word = r"\b{}\b"  # word-boundary pattern used in regex search

def classify(text: str, dictionaries: Dict[str, Set[str]]) -> Dict[str, bool]:
    """Return {category: bool, …} for one piece of text."""
    text = str(text).lower()
    return {
        cat: any(re.search(_word.format(re.escape(p)), text) for p in phrases)
        for cat, phrases in dictionaries.items()
    }

# ----------------------------------------------------------------------------
# Streamlit UI
# ----------------------------------------------------------------------------

st.set_page_config(page_title="Keyword Classifier", layout="wide")
st.title("🔍 Keyword Classifier for Marketing Copy")

st.markdown(
    """
    Upload a CSV file containing a **Statement** column (or set your own column name)
    and quickly flag rows that contain urgency or exclusivity marketing phrases—or any
    keywords you define. You can edit the default dictionaries on the sidebar. Once
    processed, download the enriched CSV with a single click.
    """
)

# -- Sidebar controls --------------------------------------------------------

st.sidebar.header("⚙️ Settings")

# 1. Upload CSV file ---------------------------------------------------------
uploaded_file = st.sidebar.file_uploader(
    "**Upload your CSV file**", type=["csv"], accept_multiple_files=False
)

# 2. Column selector ---------------------------------------------------------
statement_col = st.sidebar.text_input(
    "Column that contains the text to classify", value="Statement"
)

# 3. Dictionary editor -------------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.subheader("🗂️ Keyword Dictionaries")

# Convert default dictionaries to JSON string as a starting point
if "dictionary_json" not in st.session_state:
    st.session_state["dictionary_json"] = json.dumps(
        {k: sorted(list(v)) for k, v in get_default_dictionaries().items()},
        indent=2,
        ensure_ascii=False,
    )

dict_json = st.sidebar.text_area(
    "Edit the JSON below to modify categories or keywords.",
    height=350,
    value=st.session_state["dictionary_json"],
)

# Validate and parse JSON ----------------------------------------------------
def parse_dictionaries(json_str: str) -> Dict[str, Set[str]]:
    try:
        raw: Dict[str, Any] = json.loads(json_str)
        return {k: {str(x).lower() for x in v} for k, v in raw.items()}
    except Exception as e:
        st.sidebar.error(f"❌ Invalid JSON: {e}")
        st.stop()

user_dictionaries = parse_dictionaries(dict_json)

# -- Perform classification --------------------------------------------------

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"❌ Unable to read CSV file: {e}")
        st.stop()

    if statement_col not in df.columns:
        st.error(f"❌ Column '{statement_col}' not found in file.")
        st.stop()

    # Classify each row — use st.progress for large files --------------------
    progress_text = "Classifying rows…"
    my_bar = st.progress(0, text=progress_text)

    flags = []
    total_rows = len(df)
    for idx, statement in enumerate(df[statement_col]):
        flags.append(classify(statement, user_dictionaries))
        if total_rows >= 1000 and idx % max(total_rows // 100, 1) == 0:
            my_bar.progress(idx / total_rows, text=progress_text)
    my_bar.progress(100, text="Done!")

    flags_df = pd.DataFrame(flags)
    result_df = pd.concat([df, flags_df], axis=1)

    st.success(f"✅ Classification finished. {len(result_df)} rows processed.")

    # Show results
    st.dataframe(result_df, use_container_width=True)

    # Allow download ---------------------------------------------------------
    download_buffer = io.StringIO()
    result_df.to_csv(download_buffer, index=False)
    st.download_button(
        label="📥 Download labeled CSV",
        data=download_buffer.getvalue(),
        file_name="classified_output.csv",
        mime="text/csv",
    )
else:
    st.info("⬆️ Upload a CSV file to get started.")
