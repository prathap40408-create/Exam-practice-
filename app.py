
import re
import random
import streamlit as st
import pandas as pd
from pypdf import PdfReader

st.set_page_config(
    page_title="Competitive Exam Study",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Competitive Exam Study Tool")

if "mcqs" not in st.session_state:
    st.session_state.mcqs = []
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "test_result" not in st.session_state:
    st.session_state.test_result = False

# ---------- PDF EXTRACTION ----------

def extract_pdf(file):
    reader = PdfReader(file)
    pages = []

    for page_no, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((page_no, text))

    return pages


def split_sentences(pages):
    sentences = []

    for page_no, text in pages:
        text = re.sub(r"[ \t]+", " ", text)
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)

        for part in parts:
            part = part.strip(" \t\r\n•-")
            if len(part.split()) >= 5:
                sentences.append({
                    "text": part,
                    "page": page_no
                })

    return sentences


# ---------- SOURCE-BASED QUESTION GENERATION ----------

def make_mcqs(sentences):
    questions = []
    seen = set()

    for item in sentences:
        sentence = item["text"]
        question = None
        answer = None

        # Example: "The Solar System has 8 planets."
        match = re.search(
            r"^(.{2,100}?)\s+has\s+"
            r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s+(.{2,100})[.!?]?$",
            sentence,
            re.IGNORECASE
        )

        if match:
            subject = match.group(1).strip()
            number = match.group(2).strip()
            noun = match.group(3).strip().rstrip(".!?")

            number_words = {
                "one": "1", "two": "2", "three": "3",
                "four": "4", "five": "5", "six": "6",
                "seven": "7", "eight": "8", "nine": "9",
                "ten": "10"
            }
            answer = number_words.get(number.lower(), number)

            question = (
                f"According to the source, how many "
                f"{noun} does {subject} have?"
            )

        # Example: "The Constitution was adopted in 1949."
        if not question:
            match = re.search(
                r"^(.{3,120}?)\s+"
                r"(?:was adopted|was established|was founded|"
                r"was formed|occurred|took place)\s+in\s+"
                r"(\d{3,4})[.!?]?$",
                sentence,
                re.IGNORECASE
            )

            if match:
                subject = match.group(1).strip()
                answer = match.group(2)
                question = (
                    f"In which year, according to the source, "
                    f"was {subject} {sentence.split(' in ')[0].split()[-1].lower()}?"
                )

        if not question or not answer:
            continue

        key = question.casefold()
        if key in seen:
            continue
        seen.add(key)

        # Create distractors for numerical answers.
        if answer.isdigit():
            correct = int(answer)
            distractors = [
                str(n) for n in
                [correct - 2, correct - 1, correct + 1, correct + 2]
                if n >= 0 and n != correct
            ]
            distractors = list(dict.fromkeys(distractors))[:3]

            if len(distractors) < 3:
                continue

            options = distractors + [answer]
            random.shuffle(options)
            labels = ["A", "B", "C", "D"]
            option_map = dict(zip(labels, options))
            correct_label = next(
                label for label, value in option_map.items()
                if value == answer
            )

            questions.append({
                "question": question,
                "options": option_map,
                "answer": correct_label,
                "explanation": sentence,
                "page": item["page"]
            })

    return questions


def make_flashcards(sentences, limit):
    cards = []
    seen = set()

    for item in sentences:
        sentence = item["text"]

        # Prefer factual statements containing dates or numbers.
        if not re.search(r"\d| is | was | has | are | were ", sentence,
                         re.IGNORECASE):
            continue

        key = sentence.casefold()
        if key in seen:
            continue
        seen.add(key)

        cards.append({
            "front": "What fact does the source state?",
            "back": sentence,
            "page": item["page"]
        })

        if len(cards) >= limit:
            break

    return cards


# ---------- NAVIGATION ----------

page = st.sidebar.radio(
    "Menu",
    ["Home", "PDF to MCQ", "Mock Test", "Flashcards"]
)

if page == "Home":
    st.header("Competitive Exam Preparation")
    st.write("Create study material from your own PDF.")
    st.write("Target exams: SSC CPO, SSC CGL, RRB NTPC and more.")
    st.info("This version needs no API key.")

elif page == "PDF to MCQ":
    st.header("PDF to MCQ")

    file = st.file_uploader(
        "Upload your PDF",
        type=["pdf"],
        key="mcq_pdf"
    )

    if file and st.button("Generate up to 120 MCQs"):
        try:
            with st.spinner("Extracting PDF facts..."):
                pages = extract_pdf(file)
                sentences = split_sentences(pages)
                st.session_state.mcqs = make_mcqs(sentences)

            st.session_state.test_result = False

            if not sentences:
                st.error(
                    "No readable text found. This PDF may be scanned "
                    "and need OCR."
                )
            elif not st.session_state.mcqs:
                st.warning(
                    "No supported numerical questions were identified "
                    "by this basic generator. The PDF may still contain "
                    "many important facts."
                )
        except Exception as e:
            st.error(f"PDF error: {e}")

    questions = st.session_state.mcqs

    if questions:
        st.success(f"{len(questions)} questions generated.")

        if len(questions) < 120:
            st.info(
                "This basic free generator only supports certain "
                "fact patterns. It does not mean your PDF lacks content."
            )

        for i, q in enumerate(questions, 1):
            with st.expander(f"Q{i}. {q['question']}"):
                for label, option in q["options"].items():
                    st.write(f"{label}) {option}")

                st.write(
                    f"**Correct answer:** {q['answer']}) "
                    f"{q['options'][q['answer']]}"
                )
                st.write(f"**Explanation:** {q['explanation']}")
                st.caption(f"Source PDF page: {q['page']}")

        rows = []
        for q in questions:
            rows.append({
                "Question": q["question"],
                "Option A": q["options"]["A"],
                "Option B": q["options"]["B"],
                "Option C": q["options"]["C"],
                "Option D": q["options"]["D"],
                "Answer": q["answer"],
                "Explanation": q["explanation"],
                "PDF page": q["page"]
            })

        st.download_button(
            "Download MCQs CSV",
            pd.DataFrame(rows).to_csv(index=False),
            "mcqs.csv",
            "text/csv"
        )

elif page == "Mock Test":
    st.header("Mock Test")
    st.write("Correct: +1 | Incorrect: -0.33 | Unanswered: 0")

    questions = st.session_state.mcqs

    if not questions:
        st.info("Generate questions in the PDF to MCQ page first.")
    else:
        with st.form("mock_test"):
            answers = {}

            for i, q in enumerate(questions):
                selected = st.radio(
                    f"Q{i + 1}. {q['question']}",
                    ["Not answered", "A", "B", "C", "D"],
                    format_func=lambda x, q=q: (
                        x if x == "Not answered"
                        else f"{x}) {q['options'][x]}"
                    ),
                    key=f"answer_{i}"
                )
                answers[i] = selected

            submitted = st.form_submit_button("Submit test")

        if submitted:
            correct = 0
            wrong = 0
            unanswered = 0

            for i, q in enumerate(questions):
                selected = answers[i]

                if selected == "Not answered":
                    unanswered += 1
                elif selected == q["answer"]:
                    correct += 1
                else:
                    wrong += 1

            score = correct - 0.33 * wrong
            attempted = correct + wrong
            accuracy = correct / attempted * 100 if attempted else 0

            st.subheader("Results")
            st.write(f"Score: {score:.2f} / {len(questions)}")
            st.write(f"Correct: {correct}")
            st.write(f"Incorrect: {wrong}")
            st.write(f"Unanswered: {unanswered}")
            st.write(f"Accuracy: {accuracy:.2f}%")

            st.subheader("Answer Analysis")
            for i, q in enumerate(questions):
                st.write(f"**Q{i + 1}. {q['question']}**")
                st.write(f"Your answer: {answers[i]}")
                st.write(f"Correct answer: {q['answer']}")
                st.write(f"Explanation: {q['explanation']}")

elif page == "Flashcards":
    st.header("PDF Flashcards")

    file = st.file_uploader(
        "Upload your PDF",
        type=["pdf"],
        key="flashcard_pdf"
    )

    limit = st.selectbox(
        "Number of cards",
        [10, 20, 30, 40],
        index=3
    )

    if file and st.button("Generate Flashcards"):
        try:
            pages = extract_pdf(file)
            sentences = split_sentences(pages)
            st.session_state.flashcards = make_flashcards(
                sentences, limit
            )

            if not st.session_state.flashcards:
                st.warning(
                    "No suitable facts were identified by the "
                    "basic generator."
                )
        except Exception as e:
            st.error(f"PDF error: {e}")

    cards = st.session_state.flashcards

    for i, card in enumerate(cards, 1):
        with st.expander(f"Flashcard {i} — Tap to reveal"):
            st.markdown("**FRONT — QUESTION**")
            st.write(card["front"])
            st.divider()
            st.markdown("**BACK — ANSWER**")
            st.write(card["back"])
            st.caption(f"Source PDF page: {card['page']}")

    if cards:
        st.download_button(
            "Download Flashcards CSV",
            pd.DataFrame(cards).to_csv(index=False),
            "flashcards.csv",
            "text/csv"
            )
    
