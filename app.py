import re
import random
import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(
    page_title="My Exam Preparation",
    page_icon="📚",
    layout="wide"
)

st.title("📚 My Exam Preparation")

# ---------- SUBJECT-WISE STUDY ----------
SUBJECTS = {
    "Indian Polity": [
        "Historical Background", "Making of the Constitution",
        "Preamble", "Fundamental Rights",
        "Directive Principles", "Fundamental Duties",
        "Union and its Territory", "Citizenship"
    ],
    "History": [
        "Indus Valley Civilization", "Vedic Age",
        "Buddhism and Jainism", "Mauryan Empire",
        "Gupta Empire", "Medieval India", "Modern India"
    ],
    "Geography": [
        "Physical Geography", "Indian Geography",
        "Climate", "Rivers", "Agriculture"
    ],
    "Economics": [
        "Basic Economics", "National Income",
        "Inflation", "Banking", "Budget"
    ],
    "Science": [
        "Physics", "Chemistry", "Biology"
    ],
    "Reasoning": [
        "Analogy", "Series", "Coding-Decoding",
        "Blood Relations", "Direction", "Syllogism"
    ],
    "Quantitative Aptitude": [
        "Number System", "Percentage", "Ratio",
        "Average", "Profit and Loss", "Time and Work"
    ],
    "English": [
        "Parts of Speech", "Noun", "Pronoun",
        "Tenses", "Subject-Verb Agreement",
        "Active and Passive Voice"
    ],
    "Current Affairs": [
        "National News", "International News",
        "Economy", "Science and Technology", "Sports"
    ]
}

# ---------- RULE-BASED PDF MCQ GENERATOR ----------
def generate_mcqs(pdf_file, limit=10):
    reader = PdfReader(pdf_file)
    full_text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    )

    sentences = re.split(r"(?<=[.!?])\s+|\n+", full_text)

    pattern = re.compile(
        r"\b(?:\d{4}|\d+(?:\.\d+)?%?|"
        r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b"
    )

    facts = []
    for sentence in sentences:
        sentence = " ".join(sentence.split())
        if not 30 <= len(sentence) <= 350:
            continue

        for match in pattern.finditer(sentence):
            answer = match.group().strip()
            if answer.lower() in {
                "the", "this", "that", "these", "those",
                "when", "where", "which", "there", "however"
            }:
                continue

            question = (
                sentence[:match.start()] + "________" +
                sentence[match.end():]
            )
            facts.append({
                "question": question,
                "answer": answer,
                "sentence": sentence
            })

    unique = []
    seen = set()
    for fact in facts:
        key = (fact["question"].lower(), fact["answer"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(fact)

    answer_pool = list({f["answer"] for f in unique})
    random.shuffle(unique)
    mcqs = []

    for fact in unique:
        wrong = [
            answer for answer in answer_pool
            if answer.lower() != fact["answer"].lower()
        ]
        if len(wrong) < 3:
            continue

        options = random.sample(wrong, 3) + [fact["answer"]]
        random.shuffle(options)
        labels = ["A", "B", "C", "D"]
        correct = labels[options.index(fact["answer"])]

        mcqs.append({
            "question": fact["question"],
            "A": options[0],
            "B": options[1],
            "C": options[2],
            "D": options[3],
            "answer": correct,
            "explanation": fact["sentence"]
        })

        if len(mcqs) >= limit:
            break

    return mcqs


# ---------- SIDEBAR ----------
page = st.sidebar.radio(
    "Menu",
    [
        "Subject-wise Study",
        "Upload Documents",
        "PDF to MCQ",
        "Mock Test",
        "Flashcards"
    ]
)

# ---------- SUBJECT-WISE STUDY ----------
if page == "Subject-wise Study":
    st.header("📚 Subject-wise Study")

    subject = st.selectbox("Choose a subject", list(SUBJECTS.keys()))
    topic = st.selectbox("Choose a topic", SUBJECTS[subject])

    st.subheader(topic)
    st.write("Use this section to organize your exam preparation.")
    st.text_area(
        "Your study notes",
        key=f"notes_{subject}_{topic}",
        placeholder="Write or paste your notes here..."
    )
    st.caption("Notes stay in the current app session; download them if needed.")

# ---------- UPLOAD DOCUMENTS ----------
elif page == "Upload Documents":
    st.header("📄 Upload Documents")

    uploaded_files = st.file_uploader(
        "Upload your study PDFs",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            st.write(f"📎 {file.name} — {file.size:,} bytes")

            if st.button("Extract text", key=f"extract_{file.name}"):
                try:
                    reader = PdfReader(file)
                    text = "\n".join(
                        page.extract_text() or ""
                        for page in reader.pages
                    )
                    st.text_area(
                        "Extracted text",
                        text,
                        height=250,
                        key=f"text_{file.name}"
                    )
                except Exception:
                    st.error("Could not read this PDF.")

# ---------- PDF TO MCQ ----------
elif page == "PDF to MCQ":
    st.header("📝 Free PDF-to-MCQ Generator")
    st.write(
        "Creates basic fill-in-the-blank multiple-choice questions "
        "from text-based PDFs. No AI API or API key is used."
    )

    pdf = st.file_uploader("Upload a text-based PDF", type=["pdf"])
    count = st.slider("Number of questions", 5, 30, 10)

    if st.button("Generate MCQs", disabled=(pdf is None)):
        try:
            with st.spinner("Reading PDF and creating questions..."):
                questions = generate_mcqs(pdf, count)

            if questions:
                st.session_state["pdf_mcqs"] = questions
                st.session_state["pdf_answers"] = {}
                st.success(f"Created {len(questions)} questions.")
            else:
                st.warning(
                    "Not enough suitable text was found. "
                    "Try a PDF with selectable text and complete sentences."
                )
        except Exception as error:
            st.error("Could not read this PDF.")
            st.caption(str(error))

    questions = st.session_state.get("pdf_mcqs", [])
    if questions:
        st.subheader("Practice questions")

        for i, q in enumerate(questions):
            st.markdown(f"**Q{i + 1}. {q['question']}**")

            selected = st.radio(
                "Choose one answer",
                ["A", "B", "C", "D"],
                format_func=lambda x, q=q: f"{x}. {q[x]}",
                key=f"pdf_option_{i}",
                index=None
            )
            st.session_state["pdf_answers"][i] = selected

        if st.button("Submit PDF Test"):
            score = 0
            for i, q in enumerate(questions):
                selected = st.session_state["pdf_answers"].get(i)
                if selected == q["answer"]:
                    score += 1

            st.success(f"Your score: {score}/{len(questions)}")

            for i, q in enumerate(questions):
                st.markdown(f"**Q{i + 1}: {q['answer']}. {q[q['answer']]}**")
                st.write(f"Explanation: {q['explanation']}")

        csv_data = pd.DataFrame(questions).to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download questions as CSV",
            data=csv_data,
            file_name="pdf_mcqs.csv",
            mime="text/csv"
        )

# ---------- MOCK TEST ----------
elif page == "Mock Test":
    st.header("🧪 Mock Test")

    sample_questions = [
        {
            "question": "When was the Constitution of India adopted?",
            "A": "15 August 1947",
            "B": "26 November 1949",
            "C": "26 January 1950",
            "D": "2 October 1950",
            "answer": "B",
            "explanation": "The Constitution was adopted on 26 November 1949."
        },
        {
            "question": "Fundamental Rights are in which part?",
            "A": "Part I",
            "B": "Part II",
            "C": "Part III",
            "D": "Part IV",
            "answer": "C",
            "explanation": "Fundamental Rights are covered in Part III."
        },
        {
            "question": "Which is the largest planet in our Solar System?",
            "A": "Earth",
            "B": "Mars",
            "C": "Saturn",
            "D": "Jupiter",
            "answer": "D",
            "explanation": "Jupiter is the largest planet in our Solar System."
        },
        {
            "question": "What is 25% of 200?",
            "A": "25",
            "B": "40",
            "C": "50",
            "D": "75",
            "answer": "C",
            "explanation": "25% of 200 = 200 × 25/100 = 50."
        },
        {
            "question": "Which gas do plants absorb during photosynthesis?",
            "A": "Oxygen",
            "B": "Carbon dioxide",
            "C": "Nitrogen",
            "D": "Hydrogen",
            "answer": "B",
            "explanation": "Plants absorb carbon dioxide during photosynthesis."
        }
    ]

    for i, q in enumerate(sample_questions):
        st.markdown(f"**Q{i + 1}. {q['question']}**")
        st.radio(
            "Select answer",
            ["A", "B", "C", "D"],
            format_func=lambda x, q=q: f"{x}. {q[x]}",
            key=f"mock_{i}",
            index=None
        )

    if st.button("Submit Mock Test"):
        score = 0
        for i, q in enumerate(sample_questions):
            selected = st.session_state.get(f"mock_{i}")
            if selected == q["answer"]:
                score += 1

        st.success(f"Your score: {score}/{len(sample_questions)}")
        for i, q in enumerate(sample_questions):
            st.write(
                f"Q{i + 1}. Correct answer: "
                f"{q['answer']}. {q[q['answer']]}"
            )
            st.caption(q["explanation"])

# ---------- FLASHCARDS ----------
elif page == "Flashcards":
    st.header("🃏 Flashcards")

    cards = [
        ("When was the Constitution adopted?", "26 November 1949"),
        ("When did the Constitution come into force?", "26 January 1950"),
        ("Which Part contains Fundamental Rights?", "Part III"),
        ("Which Part contains DPSPs?", "Part IV"),
        ("Which Article deals with equality before law?", "Article 14"),
        ("Which Article abolishes untouchability?", "Article 17"),
        ("Who is the constitutional head of India?", "The President"),
        ("What is the lower house of Parliament?", "Lok Sabha"),
        ("What is the upper house of Parliament?", "Rajya Sabha"),
        ("Which body conducts elections in India?", "Election Commission of India")
    ]

    if "flash_index" not in st.session_state:
        st.session_state["flash_index"] = 0
    if "show_flash_answer" not in st.session_state:
        st.session_state["show_flash_answer"] = False

    index = st.session_state["flash_index"]
    front, back = cards[index]

    st.caption(f"Card {index + 1} of {len(cards)}")
    st.subheader(front)

    if st.button("Show / Hide Answer"):
        st.session_state["show_flash_answer"] = (
            not st.session_state["show_flash_answer"]
        )

    if st.session_state["show_flash_answer"]:
        st.success(back)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("⬅ Previous"):
            st.session_state["flash_index"] = (index - 1) % len(cards)
            st.session_state["show_flash_answer"] = False
            st.rerun()

    with col2:
        if st.button("Next ➡"):
            st.session_state["flash_index"] = (index + 1) % len(cards)
            st.session_state["show_flash_answer"] = False
            st.rerun()
