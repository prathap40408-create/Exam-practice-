
import re
import random
import hashlib
import streamlit as st
from pypdf import PdfReader

st.set_page_config(page_title="Exam Prep", page_icon="📚", layout="wide")

st.title("📚 Competitive Exam Preparation")
st.caption("SSC CPO • SSC CGL • RRB NTPC • Other competitive exams")

# ---------- SESSION DATA ----------
for key, default in {
    "questions": [],
    "flashcards": [],
    "pdf_name": "",
    "test_answers": {},
    "test_started": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---------- PDF TEXT EXTRACTION ----------
def extract_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
        except Exception:
            continue
    return "\n".join(pages), len(reader.pages)


def split_sentences(text):
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    parts = re.split(r'(?<=[.!?])\s+|\n+', text)
    return list(dict.fromkeys(
        s.strip() for s in parts
        if len(s.strip()) >= 35
        and len(s.strip().split()) >= 7
    ))


# ---------- FACT DETECTION ----------
STOP_NAMES = {
    "The", "This", "That", "These", "Those", "There", "Their",
    "However", "Therefore", "When", "Where", "Which", "What",
    "Who", "According", "During", "After", "Before", "Under",
    "Between", "Chapter", "Figure", "Table", "Example", "Note",
    "Following", "Some", "Many", "Most", "Each", "Every"
}

def find_targets(sentence):
    found = []

    # Years, dates and numeric facts
    patterns = [
        (r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b", "date"),
        (r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", "date"),
        (r"\b(?:1[5-9]\d{2}|20\d{2}|2100)\b", "year"),
        (r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b", "number"),
    ]

    for pattern, kind in patterns:
        for match in re.finditer(pattern, sentence, re.I):
            value = match.group()
            if kind == "number" and value in {"0", "1"}:
                continue
            found.append((value, kind, match.start()))

    # Names and important capitalized terms
    name_patterns = [
        r"\b[A-Z]{2,8}\b",
        r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b",
    ]

    for pattern in name_patterns:
        for match in re.finditer(pattern, sentence):
            value = match.group().strip()
            first_word = sentence[:match.start()].strip()
            if not first_word and value.split()[0] in STOP_NAMES:
                continue
            if value.split()[0] in STOP_NAMES:
                continue
            if value.lower() in {"the united", "according to"}:
                continue
            found.append((value, "name", match.start()))

    # Avoid duplicates and very short answers
    unique = {}
    for value, kind, pos in found:
        value = value.strip(" ,.;:")
        if len(value) < 2:
            continue
        key = (value.lower(), kind)
        unique[key] = (value, kind, pos)

    return list(unique.values())


def build_questions(text, limit=120):
    sentences = split_sentences(text)
    targets_by_type = {"year": set(), "date": set(),
                       "number": set(), "name": set()}

    sentence_data = []
    for sentence in sentences:
        targets = find_targets(sentence)
        for value, kind, _ in targets:
            targets_by_type.setdefault(kind, set()).add(value)
        sentence_data.append((sentence, targets))

    rng = random.Random(
        hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
    )
    questions = []
    seen = set()

    for sentence, targets in sentence_data:
        for answer, kind, pos in targets:
            # Don't create multiple identical questions
            question_text = re.sub(
                re.escape(answer), "_____",
                sentence, count=1, flags=re.I
            )
            key = re.sub(r"\W+", "", question_text.lower()) + answer.lower()
            if key in seen:
                continue

            # Prefer distractors of the same type from the PDF
            pool = [
                v for v in targets_by_type.get(kind, set())
                if v.lower() != answer.lower()
            ]

            if kind in ("year", "number"):
                try:
                    n = int(answer.replace(",", "").replace("%", ""))
                    suffix = "%" if "%" in answer else ""
                    pool += [f"{n + d}{suffix}" for d in (-3, -2, -1, 1, 2, 3)]
                except ValueError:
                    pass

            pool = list(dict.fromkeys(pool))
            pool = [v for v in pool if v.lower() != answer.lower()]
            rng.shuffle(pool)

            options = [answer]
            for value in pool:
                if value.lower() not in {x.lower() for x in options}:
                    options.append(value)
                if len(options) == 4:
                    break

            # Avoid weak or fabricated distractors for names/dates
            if len(options) < 4 and kind not in ("year", "number"):
                continue

            if len(options) < 4:
                continue

            rng.shuffle(options)
            correct_index = options.index(answer)
            question = {
                "question": (
                    "According to the PDF, complete the statement:\n\n"
                    + question_text
                ),
                "options": options,
                "answer": answer,
                "correct_index": correct_index,
                "explanation": (
                    "The PDF states: " + sentence
                ),
                "source": sentence,
            }

            seen.add(key)
            questions.append(question)

            if len(questions) >= 500:
                return questions

    return questions


# ---------- NAVIGATION ----------
page = st.sidebar.radio(
    "Choose a page",
    ["Home", "PDF to MCQ", "Mock Test", "Flashcards"]
)

if page == "Home":
    st.header("Welcome")
    st.write("Upload study material to create source-based practice questions.")
    st.write("1. Open PDF to MCQ.")
    st.write("2. Upload a text-readable PDF.")
    st.write("3. Generate questions and review the answers.")
    st.write("4. Use Mock Test and Flashcards to revise.")

elif page == "PDF to MCQ":
    st.header("PDF to MCQ Generator")
    st.info(
        "This free version uses text extraction and rule-based question "
        "generation. It does not use a paid AI API."
    )

    uploaded = st.file_uploader("Upload your PDF", type=["pdf"])
    desired = st.number_input(
        "Questions to generate",
        min_value=20,
        max_value=500,
        value=120,
        step=10
    )

    if st.button("Generate Questions", type="primary"):
        if uploaded is None:
            st.error("Please upload a PDF first.")
        else:
            with st.spinner("Reading the PDF and identifying facts..."):
                try:
                    text, page_count = extract_pdf(uploaded)
                    if len(text.strip()) < 100:
                        st.error(
                            "Very little readable text was found. "
                            "This PDF may be scanned; OCR is needed."
                        )
                    else:
                        all_questions = build_questions(text, 500)
                        st.session_state.pdf_name = uploaded.name
                        st.session_state.questions = all_questions[:int(desired)]
                        st.session_state.flashcards = [
                            {
                                "front": q["question"],
                                "back": q["answer"],
                                "explanation": q["explanation"],
                            }
                            for q in all_questions[:int(desired)]
                        ]
                        st.session_state.test_answers = {}
                        st.session_state.test_started = False

                        st.success(
                            f"Read {page_count} PDF pages. "
                            f"Generated {len(st.session_state.questions)} "
                            f"usable questions."
                        )
                        if len(all_questions) < int(desired):
                            st.warning(
                                f"The rule-based generator found only "
                                f"{len(all_questions)} usable questions. "
                                "It will not invent extra questions to fill "
                                "the requested count."
                            )
                except Exception as e:
                    st.error(f"Could not read this PDF: {e}")

    questions = st.session_state.questions
    if questions:
        st.subheader(f"Generated questions: {len(questions)}")
        st.caption(f"Source PDF: {st.session_state.pdf_name}")

        for i, q in enumerate(questions, start=1):
            with st.expander(f"Question {i}: {q['question'][:90]}"):
                st.write(q["question"])
                for j, option in enumerate(q["options"]):
                    st.write(f"{chr(65+j)}. {option}")
                st.write(f"**Correct answer:** {q['answer']}")
                st.write(f"**Explanation:** {q['explanation']}")

        export_text = ""
        for i, q in enumerate(questions, start=1):
            export_text += f"{i}. {q['question']}\n"
            for j, option in enumerate(q["options"]):
                export_text += f"   {chr(65+j)}. {option}\n"
            export_text += (
                f"Answer: {q['answer']}\n"
                f"Explanation: {q['explanation']}\n\n"
            )
        st.download_button(
            "Download MCQs as TXT",
            data=export_text,
            file_name="pdf_mcqs.txt",
            mime="text/plain"
        )

elif page == "Mock Test":
    st.header("Mock Test")
    questions = st.session_state.questions

    if not questions:
        st.warning("Generate questions from a PDF first.")
    else:
        count = min(120, len(questions))
        st.caption(
            f"Questions: {count} | Correct: +1 | Incorrect: −0.33 | "
            "Unanswered: 0"
        )

        if st.button("Start / Reset Test"):
            st.session_state.test_started = True
            st.session_state.test_answers = {}

        if st.session_state.test_started:
            with st.form("mock_test_form"):
                answers = {}
                for i, q in enumerate(questions[:count]):
                    st.markdown(f"**Q{i+1}. {q['question']}**")
                    answers[i] = st.radio(
                        "Choose one",
                        ["Not answered"] + [
                            f"{chr(65+j)}. {option}"
                            for j, option in enumerate(q["options"])
                        ],
                        key=f"test_{i}",
                        label_visibility="collapsed"
                    )
                submitted = st.form_submit_button("Submit Test")

            if submitted:
                correct = wrong = unanswered = 0
                review = []
                for i, q in enumerate(questions[:count]):
                    selected = answers[i]
                    if selected == "Not answered":
                        unanswered += 1
                    else:
                        selected_letter = selected[0]
                        if selected_letter == chr(65 + q["correct_index"]):
                            correct += 1
                        else:
                            wrong += 1
                    review.append((i + 1, q, selected))

                score = correct - (wrong * 0.33)
                st.subheader(f"Score: {score:.2f} / {count}")
                st.write(
                    f"Correct: {correct} | Incorrect: {wrong} | "
                    f"Unanswered: {unanswered}"
                )
                for number, q, selected in review:
                    with st.expander(f"Review Q{number}"):
                        st.write(q["question"])
                        st.write(f"Your answer: {selected}")
                        st.write(f"Correct answer: {q['answer']}")
                        st.write(f"Explanation: {q['explanation']}")

elif page == "Flashcards":
    st.header("Flashcards")
    cards = st.session_state.flashcards

    if not cards:
        st.warning("Generate questions from a PDF first.")
    else:
        index = st.number_input(
            "Flashcard number",
            min_value=1,
            max_value=len(cards),
            value=1
        )
        card = cards[int(index) - 1]
        st.markdown("### Front — Question")
        st.write(card["front"])
        if st.button("Reveal Answer"):
            st.session_state["reveal_card"] = int(index)
        if st.session_state.get("reveal_card") == int(index):
            st.markdown("### Back — Answer")
            st.success(card["back"])
            st.write(card["explanation"])
        
