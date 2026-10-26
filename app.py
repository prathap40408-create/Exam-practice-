
import re
import random
import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(
    page_title="My Exam Preparation",
    page_icon="📚",
    layout="centered"
)

st.title("📚 My Exam Preparation")

# ---------- PDF TO MCQ FUNCTION ----------

def generate_mcqs(pdf_file, limit=10):
    reader = PdfReader(pdf_file)

    text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

    pattern = re.compile(
        r"\b(?:"
        r"\d{4}"
        r"|\d+(?:\.\d+)?%?"
        r"|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
        r")\b"
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
                sentence[:match.start()]
                + "________"
                + sentence[match.end():]
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

    answer_pool = list({
        fact["answer"] for fact in unique
    })

    if len(answer_pool) < 4:
        return []

    random.shuffle(unique)
    mcqs = []

    for fact in unique:
        wrong = [
            answer for answer in answer_pool
            if answer.lower() != fact["answer"].lower()
        ]

        if len(wrong) < 3:
            continue

        options = random.sample(wrong, 3)
        options.append(fact["answer"])
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


# ---------- MENU ----------

st.sidebar.title("Menu")

page = st.sidebar.radio(
    "Choose a feature",
    [
        "Home",
        "Upload Documents",
        "PDF to MCQ",
        "Mock Test",
        "Flashcards"
    ]
)

if "questions" not in st.session_state:
    st.session_state.questions = []

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

if "mock_score" not in st.session_state:
    st.session_state.mock_score = None


# ---------- HOME ----------

if page == "Home":
    st.header("Welcome!")

    st.write("Your free exam preparation website.")

    st.markdown("""
    - 📄 Upload Documents
    - 📝 PDF to MCQ Generator
    - 🎯 Mock Test
    - 🗂️ Flashcards

    Use the menu on the left to begin.
    """)


# ---------- UPLOAD DOCUMENTS ----------

elif page == "Upload Documents":
    st.header("📄 Upload Documents")

    pdf = st.file_uploader(
        "Upload your PDF notes",
        type=["pdf"],
        key="document_pdf"
    )

    if pdf:
        st.success(f"Uploaded: {pdf.name}")
        st.info(
            "Use the PDF to MCQ page to create practice questions."
        )


# ---------- PDF TO MCQ ----------

elif page == "PDF to MCQ":
    st.header("📝 Free PDF to MCQ Generator")

    st.write(
        "Creates basic fill-in-the-blank multiple-choice "
        "questions using text extracted from your PDF."
    )

    pdf = st.file_uploader(
        "Choose a text-based PDF",
        type=["pdf"],
        key="mcq_pdf"
    )

    count = st.slider(
        "Number of questions",
        min_value=5,
        max_value=30,
        value=10
    )

    if st.button(
        "Generate MCQs",
        disabled=(pdf is None)
    ):
        try:
            with st.spinner("Reading your PDF..."):
                questions = generate_mcqs(pdf, count)

            st.session_state.questions = questions
            st.session_state.mock_score = None

            if questions:
                st.success(
                    f"Generated {len(questions)} questions."
                )
            else:
                st.warning(
                    "Not enough suitable text was found. "
                    "Try a text-based PDF with clear sentences."
                )

        except Exception as error:
            st.error("Could not read this PDF.")
            st.caption(str(error))

    questions = st.session_state.questions

    if questions:
        st.subheader("Practice Questions")

        for i, q in enumerate(questions):
            st.markdown(
                f"**Q{i + 1}. {q['question']}**"
            )

            st.radio(
                "Select your answer",
                ["A", "B", "C", "D"],
                format_func=lambda x, q=q: f"{x}. {q[x]}",
                key=f"pdf_answer_{i}",
                index=None
            )

            with st.expander("Show answer and explanation"):
                st.write(
                    f"Correct answer: {q['answer']}. "
                    f"{q[q['answer']]}"
                )
                st.write(q["explanation"])

        csv_data = pd.DataFrame(questions).to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Questions as CSV",
            data=csv_data,
            file_name="pdf_mcqs.csv",
            mime="text/csv"
        )


# ---------- MOCK TEST ----------

elif page == "Mock Test":
    st.header("🎯 Mock Test")

    questions = st.session_state.questions

    if not questions:
        st.info(
            "First generate questions on the PDF to MCQ page."
        )
    else:
        st.write(f"Total questions: {len(questions)}")

        with st.form("mock_test_form"):
            answers = {}

            for i, q in enumerate(questions):
                st.markdown(
                    f"**Q{i + 1}. {q['question']}**"
                )

                answers[i] = st.radio(
                    "Choose one",
                    ["A", "B", "C", "D"],
                    format_func=lambda x, q=q: f"{x}. {q[x]}",
                    key=f"mock_{i}",
                    index=None
                )

            submitted = st.form_submit_button(
                "Submit Mock Test"
            )

        if submitted:
            score = sum(
                answers[i] == q["answer"]
                for i, q in enumerate(questions)
            )

            st.session_state.mock_score = score

        if st.session_state.mock_score is not None:
            score = st.session_state.mock_score

            st.subheader(
                f"Your Score: {score}/{len(questions)}"
            )

            for i, q in enumerate(questions):
                st.markdown(
                    f"**Q{i + 1}. {q['question']}**"
                )

                st.write(
                    f"Correct answer: {q['answer']}. "
                    f"{q[q['answer']]}"
                )

                st.write(f"Explanation: {q['explanation']}")


# ---------- FLASHCARDS ----------

elif page == "Flashcards":
    st.header("🗂️ Flashcards")

    st.write("Create your own question-and-answer cards.")

    with st.form("flashcard_form", clear_on_submit=True):
        front = st.text_input("Question or term")
        back = st.text_input("Answer or definition")

        add_card = st.form_submit_button("Add Flashcard")

    if add_card:
        if front.strip() and back.strip():
            st.session_state.flashcards.append({
                "front": front.strip(),
                "back": back.strip()
            })
            st.success("Flashcard added.")
        else:
            st.warning("Enter both a question and an answer.")

    cards = st.session_state.flashcards

    if cards:
        st.write(f"Total flashcards: {len(cards)}")

        for i, card in enumerate(cards):
            with st.expander(
                f"Card {i + 1}: {card['front']}"
            ):
                st.write(f"**Answer:** {card['back']}")

        if st.button("Clear All Flashcards"):
            st.session_state.flashcards = []
            st.rerun()
    else:
        st.info("Your flashcards will appear here.")
    
