import re
import random
import pandas as pd

import streamlit as st
import random

st.set_page_config(
    page_title="SSC Exam Practice",
    page_icon="📚",
    layout="centered"
)

st.title("📚 SSC Exam Practice")

# Sample questions. Add more unique questions here.
QUESTION_BANK = [
    {
        "id": 1,
        "topic": "Polity",
        "question": "When was the Constitution of India adopted?",
        "options": ["15 August 1947", "26 November 1949",
                    "26 January 1950", "2 October 1950"],
        "answer": "B",
        "explanation": "The Constituent Assembly adopted the Constitution on 26 November 1949."
    },
    {
        "id": 2,
        "topic": "Polity",
        "question": "When did the Constitution of India come into force?",
        "options": ["15 August 1947", "26 November 1949",
                    "26 January 1950", "26 January 1949"],
        "answer": "C",
        "explanation": "The Constitution came into force on 26 January 1950."
    },
    {
        "id": 3,
        "topic": "Polity",
        "question": "Who was the Chairman of the Drafting Committee?",
        "options": ["Jawaharlal Nehru", "B. R. Ambedkar",
                    "Rajendra Prasad", "Sardar Patel"],
        "answer": "B",
        "explanation": "Dr. B. R. Ambedkar chaired the Drafting Committee."
    },
    {
        "id": 4,
        "topic": "History",
        "question": "The Great Bath was discovered at which site?",
        "options": ["Harappa", "Lothal", "Mohenjo-daro", "Kalibangan"],
        "answer": "C",
        "explanation": "The Great Bath is a famous structure at Mohenjo-daro."
    },
    {
        "id": 5,
        "topic": "History",
        "question": "Who founded the Mauryan Empire?",
        "options": ["Ashoka", "Chandragupta Maurya",
                    "Bindusara", "Harsha"],
        "answer": "B",
        "explanation": "Chandragupta Maurya founded the Mauryan Empire."
    },
    {
        "id": 6,
        "topic": "Geography",
        "question": "Which is the largest state in India by area?",
        "options": ["Madhya Pradesh", "Maharashtra",
                    "Rajasthan", "Uttar Pradesh"],
        "answer": "C",
        "explanation": "Rajasthan is India's largest state by area."
    },
    {
        "id": 7,
        "topic": "Science",
        "question": "What is the SI unit of force?",
        "options": ["Joule", "Watt", "Newton", "Pascal"],
        "answer": "C",
        "explanation": "The SI unit of force is the newton."
    },
    {
        "id": 8,
        "topic": "Economics",
        "question": "Which institution issues most currency notes in India?",
        "options": ["SBI", "RBI", "SEBI", "NABARD"],
        "answer": "B",
        "explanation": "The Reserve Bank of India issues banknotes, except the one-rupee note."
    },
    {
        "id": 9,
        "topic": "Polity",
        "question": "Fundamental Rights are mainly contained in which part?",
        "options": ["Part I", "Part II", "Part III", "Part IV"],
        "answer": "C",
        "explanation": "Fundamental Rights are contained in Part III of the Constitution."
    },
    {
        "id": 10,
        "topic": "History",
        "question": "Who was the first Mughal emperor of India?",
        "options": ["Akbar", "Babur", "Humayun", "Shah Jahan"],
        "answer": "B",
        "explanation": "Babur founded the Mughal Empire in India in 1526."
    },
]

# Track used question IDs during the current app session.
if "used_ids" not in st.session_state:
    st.session_state.used_ids = []

if "current_set" not in st.session_state:
    st.session_state.current_set = []

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

page = st.sidebar.radio(
    "Menu",
    ["Home", "Mock Test", "Flashcards"]
)

if page == "Home":
    st.header("Welcome!")
    st.write("Practice SSC CPO, CGL, RRB NTPC and other exams.")
    st.write(f"Unique questions in bank: {len(QUESTION_BANK)}")
    st.write(f"Questions already used: {len(st.session_state.used_ids)}")
    st.warning(
        "The sample bank is not yet large enough for a 120-question test. "
        "Add at least 120 unique questions to enable a full test."
    )

elif page == "Mock Test":
    st.header("🎯 Mock Test")
    st.write("Correct: +1 | Incorrect: −0.33 | Unanswered: 0")

    available = [
        q for q in QUESTION_BANK
        if q["id"] not in st.session_state.used_ids
    ]

    test_size = 120

    if not st.session_state.current_set:
        if len(available) >= test_size:
            st.info(f"{len(available)} unused questions are available.")
            if st.button("Start New 120-Question Test"):
                st.session_state.current_set = random.sample(
                    available, test_size
                )
                st.session_state.submitted = False
                st.rerun()
        else:
            st.warning(
                f"Only {len(available)} unused questions are available. "
                f"Add at least {test_size - len(available)} more unique "
                "questions before starting a 120-question test."
            )

    else:
        questions = st.session_state.current_set

        if not st.session_state.submitted:
            with st.form("mock_test_form"):
                answers = {}

                for i, q in enumerate(questions):
                    st.markdown(
                        f"**Q{i + 1}. [{q['topic']}] {q['question']}**"
                    )

                    choices = ["A", "B", "C", "D"]
                    answers[q["id"]] = st.radio(
                        "Choose your answer",
                        choices,
                        format_func=lambda letter, q=q: (
                            f"{letter}. {q['options'][ord(letter) - 65]}"
                        ),
                        key=f"answer_{q['id']}",
                        index=None
                    )

                submitted = st.form_submit_button("Submit Test")

            if submitted:
                result = []

                for q in questions:
                    chosen = answers[q["id"]]
                    correct = q["answer"]

                    if chosen is None:
                        marks = 0
                        status = "Unanswered"
                    elif chosen == correct:
                        marks = 1
                        status = "Correct"
                    else:
                        marks = -0.33
                        status = "Incorrect"

                    result.append({
                        "question": q,
                        "chosen": chosen,
                        "status": status,
                        "marks": marks
                    })

                st.session_state.test_result = result
                st.session_state.used_ids.extend(
                    q["id"] for q in questions
                )
                st.session_state.submitted = True
                st.rerun()

        else:
            result = st.session_state.get("test_result", [])

            correct_count = sum(
                item["status"] == "Correct" for item in result
            )
            wrong_count = sum(
                item["status"] == "Incorrect" for item in result
            )
            blank_count = sum(
                item["status"] == "Unanswered" for item in result
            )
            attempted = correct_count + wrong_count
            score = sum(item["marks"] for item in result)
            accuracy = (
                correct_count / attempted * 100 if attempted else 0
            )

            st.subheader("📊 Test Analysis")
            st.metric("Net Score", f"{score:.2f} / {len(result)}")
            st.metric("Accuracy", f"{accuracy:.2f}%")
            st.write(f"✅ Correct: {correct_count}")
            st.write(f"❌ Incorrect: {wrong_count}")
            st.write(f"⭕ Unanswered: {blank_count}")
            st.write(f"📝 Attempted: {attempted}")

            st.subheader("Answer Review")

            for i, item in enumerate(result):
                q = item["question"]
                st.markdown(
                    f"**Q{i + 1}. {q['question']}**"
                )
                st.write(
                    f"Your answer: {item['chosen'] or 'Not answered'}"
                )
                st.write(
                    f"Correct answer: {q['answer']}. "
                    f"{q['options'][ord(q['answer']) - 65]}"
                )
                st.write(f"Result: {item['status']}")
                st.caption(f"Explanation: {q['explanation']}")

            if st.button("Prepare Next Set"):
                st.session_state.current_set = []
                st.session_state.submitted = False
                st.rerun()

elif page == "Flashcards":
    st.header("🗂️ Flashcards")

    with st.form("add_flashcard", clear_on_submit=True):
        front = st.text_input("Question or term")
        back = st.text_input("Answer")
        add = st.form_submit_button("Add Flashcard")

    if add:
        if front.strip() and back.strip():
            st.session_state.flashcards.append({
                "front": front.strip(),
                "back": back.strip()
            })
            st.success("Flashcard added.")
        else:
            st.warning("Enter both the question and answer.")

    for i, card in enumerate(st.session_state.flashcards):
        with st.expander(f"Card {i + 1}: {card['front']}"):
            st.write(card["back"])
