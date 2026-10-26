
import re
import random
import json
import os
import pandas as pd
import streamlit as st
from pypdf import PdfReader

st.set_page_config(
    page_title="My Exam Preparation",
    page_icon="📚",
    layout="centered"
)

st.title("📚 My Exam Preparation")

# ---------- QUESTION BANK ----------
# Add more unique questions here over time.
QUESTION_BANK = [
    {
        "id": "polity001",
        "subject": "Polity",
        "question": "When was the Constitution of India adopted?",
        "options": ["15 August 1947", "26 November 1949",
                    "26 January 1950", "2 October 1950"],
        "answer": "B",
        "explanation": "The Constituent Assembly adopted the Constitution on 26 November 1949."
    },
    {
        "id": "polity002",
        "subject": "Polity",
        "question": "When did the Constitution of India come into force?",
        "options": ["15 August 1947", "26 November 1949",
                    "26 January 1950", "26 January 1949"],
        "answer": "C",
        "explanation": "The Constitution came into force on 26 January 1950."
    },
    {
        "id": "history001",
        "subject": "History",
        "question": "Which Harappan site is famous for its dockyard?",
        "options": ["Harappa", "Lothal", "Kalibangan", "Ropar"],
        "answer": "B",
        "explanation": "Lothal in Gujarat is known for its ancient dockyard."
    },
    {
        "id": "history002",
        "subject": "History",
        "question": "Who founded the Mauryan Empire?",
        "options": ["Ashoka", "Bindusara", "Chandragupta Maurya", "Bimbisara"],
        "answer": "C",
        "explanation": "Chandragupta Maurya founded the Mauryan Empire."
    },
    {
        "id": "geography001",
        "subject": "Geography",
        "question": "Which is the longest river flowing entirely within India?",
        "options": ["Ganga", "Godavari", "Narmada", "Krishna"],
        "answer": "B",
        "explanation": "The Godavari is commonly described as the longest river flowing entirely within India."
    },
    {
        "id": "science001",
        "subject": "Science",
        "question": "What is the SI unit of force?",
        "options": ["Joule", "Watt", "Newton", "Pascal"],
        "answer": "C",
        "explanation": "Force is measured in newtons."
    },
    {
        "id": "science002",
        "subject": "Science",
        "question": "Which vitamin is produced in the skin with sunlight exposure?",
        "options": ["Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D"],
        "answer": "D",
        "explanation": "Sunlight exposure enables the skin to produce vitamin D."
    },
    {
        "id": "economics001",
        "subject": "Economics",
        "question": "Which institution issues most currency notes in India?",
        "options": ["SBI", "RBI", "SEBI", "NABARD"],
        "answer": "B",
        "explanation": "The Reserve Bank of India issues banknotes, except the one-rupee note."
    },
]

# ---------- USED QUESTION HISTORY ----------
HISTORY_FILE = "used_questions.json"

def load_used_ids():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return set(json.load(file))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()

def save_used_ids(ids):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as file:
            json.dump(sorted(ids), file)
    except OSError:
        st.warning("Question history could not be saved permanently.")

if "used_ids" not in st.session_state:
    st.session_state.used_ids = load_used_ids()

if "test_questions" not in st.session_state:
    st.session_state.test_questions = []

if "test_submitted" not in st.session_state:
    st.session_state.test_submitted = False

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

# ---------- PDF TO MCQ ----------
def generate_mcqs(pdf_file, limit=10):
    reader = PdfReader(pdf_file)
    text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    )
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
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
                sentence[:match.start()] + "________"
                + sentence[match.end():]
            )
            facts.append({
                "question": question,
                "answer_text": answer,
                "explanation": sentence
            })

    unique = []
    seen = set()
    for fact in facts:
        key = (fact["question"].lower(), fact["answer_text"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(fact)

    answer_pool = list({f["answer_text"] for f in unique})
    if len(answer_pool) < 4:
        return []

    random.shuffle(unique)
    result = []

    for fact in unique:
        wrong = [
            a for a in answer_pool
            if a.lower() != fact["answer_text"].lower()
        ]
        if len(wrong) < 3:
            continue

        options = random.sample(wrong, 3) + [fact["answer_text"]]
        random.shuffle(options)
        labels = ["A", "B", "C", "D"]
        correct = labels[options.index(fact["answer_text"])]

        result.append({
            "id": "pdf_" + str(len(result)),
            "subject": "PDF",
            "question": fact["question"],
            "options": options,
            "answer": correct,
            "explanation": fact["explanation"]
        })

        if len(result) >= limit:
            break

    return result

# ---------- SIDEBAR ----------
page = st.sidebar.radio(
    "Menu",
    ["Home", "PDF to MCQ", "Mock Test", "Flashcards"]
)

# ---------- HOME ----------
if page == "Home":
    st.subheader("Welcome to your exam preparation website")
    st.write("Practise MCQs, take mock tests, and revise with flashcards.")
    st.write("Mock test scoring: +1 correct, −0.33 incorrect, 0 unanswered.")

# ---------- PDF TO MCQ ----------
elif page == "PDF to MCQ":
    st.header("📄 PDF to MCQ")
    pdf = st.file_uploader("Choose a text-based PDF", type=["pdf"])
    count = st.slider(
    "Number of MCQs",
    min_value=120,
    max_value=500,
    value=620
    )

    if st.button("Generate MCQs", disabled=(pdf is None)):
        try:
            questions = generate_mcqs(pdf, count)
            st.session_state.pdf_questions = questions
            if questions:
                st.success(f"Generated {len(questions)} questions.")
            else:
                st.warning("Not enough suitable text found in this PDF.")
        except Exception as error:
            st.error("Could not read this PDF.")
            st.caption(str(error))

    for i, q in enumerate(st.session_state.get("pdf_questions", [])):
        st.markdown(f"**Q{i + 1}. {q['question']}**")
        options = q["options"]
        labels = ["A", "B", "C", "D"]
        st.radio(
            "Choose your answer",
            labels,
            format_func=lambda x, opts=options: f"{x}. {opts[labels.index(x)]}",
            key=f"pdf_{i}",
            index=None
        )
        with st.expander("Answer and explanation"):
            st.write(f"Answer: {q['answer']}. {options[labels.index(q['answer'])]}")
            st.write(q["explanation"])

# ---------- MOCK TEST ----------
elif page == "Mock Test":
    st.header("🎯 120-Question Mock Test")

    available = [
        q for q in QUESTION_BANK
        if q["id"] not in st.session_state.used_ids
    ]

    st.write(f"Questions currently in bank: {len(QUESTION_BANK)}")
    st.write(f"Unused questions remaining: {len(available)}")

    if len(available) < 120:
        st.warning(
            f"You need 120 unused questions for a full test. "
            f"Currently only {len(available)} are available. "
            "Add more unique questions to QUESTION_BANK to enable a full set."
        )

    if st.button(
        "Start New 120-Question Set",
        disabled=(len(available) < 120)
    ):
        st.session_state.test_questions = random.sample(available, 120)
        st.session_state.test_submitted = False
        st.session_state.mock_answers = {}

    questions = st.session_state.test_questions

    if questions:
        if not st.session_state.test_submitted:
            with st.form("mock_form"):
                for i, q in enumerate(questions):
                    st.markdown(f"**Q{i + 1}. {q['question']}**")
                    st.radio(
                        "Select one option",
                        ["A", "B", "C", "D"],
                        format_func=lambda x, q=q: (
                            f"{x}. {q['options'][ord(x) - ord('A')]}"
                        ),
                        key=f"mock_answer_{q['id']}",
                        index=None
                    )

                submitted = st.form_submit_button("Submit Test")

            if submitted:
                answers = {
                    q["id"]: st.session_state.get(f"mock_answer_{q['id']}")
                    for q in questions
                }
                st.session_state.mock_answers = answers
                st.session_state.test_submitted = True

                st.session_state.used_ids.update(
                    q["id"] for q in questions
                )
                save_used_ids(st.session_state.used_ids)
                st.rerun()

        else:
            answers = st.session_state.mock_answers
            correct = sum(
                answers.get(q["id"]) == q["answer"]
                for q in questions
            )
            incorrect = sum(
                answers.get(q["id"]) is not None
                and answers.get(q["id"]) != q["answer"]
                for q in questions
            )
            unanswered = len(questions) - correct - incorrect
            score = correct - (incorrect * 0.33)
            attempted = correct + incorrect
            accuracy = (correct / attempted * 100) if attempted else 0

            st.subheader("📊 Your Performance Analysis")
            c1, c2 = st.columns(2)
            c1.metric("Net Score", f"{score:.2f} / 120")
            c2.metric("Accuracy", f"{accuracy:.2f}%")

            c3, c4, c5 = st.columns(3)
            c3.metric("Correct", correct)
            c4.metric("Incorrect", incorrect)
            c5.metric("Unanswered", unanswered)

            st.write("Accuracy is correct answers divided by attempted questions.")
            st.write("Negative marking: 0.33 marks deducted per incorrect answer.")

            st.subheader("Answer Review")
            for i, q in enumerate(questions):
                user_answer = answers.get(q["id"])
                st.markdown(f"**Q{i + 1}. {q['question']}**")
                st.write(
                    "Your answer: " +
                    (user_answer if user_answer else "Unanswered")
                )
                st.write(
                    f"Correct answer: {q['answer']}. "
                    f"{q['options'][ord(q['answer']) - ord('A')]}"
                )
                st.write(f"Explanation: {q['explanation']}")

            if st.button("Clear Current Test"):
                st.session_state.test_questions = []
                st.session_state.test_submitted = False
                st.session_state.mock_answers = {}
                st.rerun()


# ---------- FLASHCARDS ----------
elif page == "Flashcards":
    st.header("🗂️ Flashcards from PDF")

    pdf = st.file_uploader(
        "Upload your study notes (PDF)",
        type=["pdf"],
        key="flashcard_pdf"
    )

    if pdf is not None:
        if st.button("Create Flashcards"):
            try:
                reader = PdfReader(pdf)

                text = "\n".join(
                    page.extract_text() or ""
                    for page in reader.pages
                )

                sentences = re.split(
                    r"(?<=[.!?])\s+|\n+",
                    text
                )

                cards = []

                for sentence in sentences:
                    sentence = " ".join(sentence.split())

                    if len(sentence) < 30:
                        continue

                    match = re.search(
                        r"\b\d{4}\b|\b[A-Z][a-z]{3,}\b",
                        sentence
                    )

                    if match:
                        term = match.group()
                        question = sentence.replace(
                            term, "________", 1
                        )

                        cards.append({
                            "front": question,
                            "back": term + " — " + sentence
                        })

                unique_cards = []
                seen = set()

                for card in cards:
                    key = card["front"].lower()

                    if key not in seen:
                        seen.add(key)
                        unique_cards.append(card)

                st.session_state.flashcards = unique_cards

                if unique_cards:
                    st.success(
                        f"Created {len(unique_cards)} flashcards."
                    )
                else:
                    st.warning(
                        "No suitable text found. Try a text-based PDF."
                    )

            except Exception as error:
                st.error("Could not read this PDF.")
                st.caption(str(error))

    cards = st.session_state.flashcards

    if cards:
        st.subheader("Your Flashcards")

        for i, card in enumerate(cards):
            with st.expander(f"Flashcard {i + 1}"):
                st.write("**Question:**")
                st.write(card["front"])
                st.write("**Answer:**")
                st.write(card["back"])

        csv_data = pd.DataFrame(cards).to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download Flashcards",
            data=csv_data,
            file_name="flashcards.csv",
            mime="text/csv"
        )
        
