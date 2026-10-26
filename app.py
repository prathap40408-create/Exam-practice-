import re
import random
import pandas as pd
import streamlit as st
from pypdf import PdfReader
streamlit
pandas
pypdf
st.set_page_config(page_title="My Exam Preparation", layout="wide")

st.title 
def generate_mcqs(pdf_file, limit=10):
    reader = PdfReader(pdf_file)
    text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    # Split extracted text into sentences.
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

    # Candidate answers: dates, numbers, and capitalized names.
    candidates = re.compile(
        r"\b(?:"
        r"\d{4}"
        r"|\d+(?:\.\d+)?%?"
        r"|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
        r")\b"
    )

    facts = []

    for sentence in sentences:
        sentence = " ".join(sentence.split())

        if len(sentence) < 30 or len(sentence) > 350:
            continue

        matches = list(candidates.finditer(sentence))

        for match in matches:
            answer = match.group().strip()

            # Ignore very short or common sentence-start words.
            if answer.lower() in {
                "the", "this", "that", "these", "those",
                "when", "where", "which", "there", "however"
            }:
                continue

            if len(answer) < 2:
                continue

            question = (
                sentence[:match.start()]
                + "________"
                + sentence[match.end():]
            )

            # Avoid questions that become empty or too short.
            if len(question) < 20:
                continue

            facts.append({
                "question": question,
                "answer": answer
            })

    # Remove duplicate question-answer pairs.
    unique = []
    seen = set()

    for fact in facts:
        key = (
            fact["question"].lower(),
            fact["answer"].lower()
        )
        if key not in seen:
            seen.add(key)
            unique.append(fact)

    if len(unique) < 2:
        return []

    # Use other extracted answers as distractors.
    answer_pool = list({
        fact["answer"] for fact in unique
    })

    random.shuffle(unique)
    mcqs = []

    for fact in unique:
        wrong = [
            item for item in answer_pool
            if item.lower() != fact["answer"].lower()
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
            "explanation": (
                "The answer is based on the extracted "
                "sentence: " + fact["question"].replace(
                    "________", fact["answer"]
                )
            )
        })

        if len(mcqs) >= limit:
            break

    return mcqs
    ("📚 My Exam Preparation")
st.write("SSC CPO | SSC CGL | RRB NTPC | IB ACIO | CAPF AC")

st.sidebar.title("Menu")
page = st.sidebar.radio(
    "Choose a section",
    ["Home", "Upload Questions", "Mock Test", "Flashcards"]
)

if page == "Home":
    st.success("Your exam preparation website is working!")
    st.write("Upload your question bank to start practising.")
    st.write("You can add questions for all your target exams.")

    
elif page == "Upload Documents":
    st.header("📄 Free PDF-to-MCQ Generator")
    st.write(
        "Generate basic practice questions from your PDF. "
        "No AI API or API key required."
    )

    pdf = st.file_uploader(
        "Upload your exam notes",
        type=["pdf"]
    )

    count = st.slider(
        "Number of questions",
        min_value=5,
        max_value=30,
        value=10
    )

    if st.button("Generate MCQs", disabled=(pdf is None)):
        try:
            with st.spinner("Extracting text and making questions..."):
                questions = generate_mcqs(pdf, count)

            if questions:
                st.session_state["rule_mcqs"] = questions
                st.success(
                    f"Created {len(questions)} questions."
                )
            else:
                st.warning(
                    "Not enough suitable text was found. "
                    "Try a text-based PDF with clear sentences."
                )

        except Exception as error:
            st.error(
                "Could not read this PDF. It may be scanned, "
                "password-protected, or damaged."
            )
            st.caption(str(error))

    questions = st.session_state.get("rule_mcqs", [])

    if questions:
        st.subheader("Practice questions")

        for i, q in enumerate(questions):
            st.markdown(
                f"**Q{i + 1}. {q['question']}**"
            )

            selected = st.radio(
                "Choose one answer",
                ["A", "B", "C", "D"],
                format_func=lambda x, q=q: (
                    f"{x}. {q[x]}"
                ),
                key=f"rule_answer_{i}",
                index=None
            )

            if st.button("Check answer", key=f"rule_check_{i}"):
                if selected is None:
                    st.warning("Select an option first.")
                elif selected == q["answer"]:
                    st.success("Correct!")
                else:
                    st.error(
                        f"Correct answer: {q['answer']}. "
                        f"{q[q['answer']]}"
                    )

                st.info(q["explanation"])

        csv_data = pd.DataFrame(questions).to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "Download questions as CSV",
            data=csv_data,
            file_name="pdf_mcqs.csv",
            mime="text/csv"
        )
        
    st.header("Upload Your Question Bank")

    uploaded_file = st.file_uploader(
        "Choose your questions CSV file",
        type=["csv"]
    )

    if uploaded_file is not None:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(
                uploaded_file,
                sep=None,
                engine="python",
                encoding="utf-8-sig"
            )

            # Clean spaces, capital letters and common heading variations
            def clean_heading(name):
                return "".join(
                    ch for ch in str(name).strip().lower()
                    if ch.isalnum()
                )

            aliases = {
                "exam": "exam",
                "subject": "subject",
                "question": "question",
                "a": "A",
                "optiona": "A",
                "b": "B",
                "optionb": "B",
                "c": "C",
                "optionc": "C",
                "d": "D",
                "optiond": "D",
                "answer": "answer",
                "correctanswer": "answer",
                "explanation": "explanation"
            }

            df.columns = [
                aliases.get(clean_heading(col), str(col).strip())
                for col in df.columns
            ]

            required = [
                "exam", "subject", "question",
                "A", "B", "C", "D",
                "answer", "explanation"
            ]

            st.write("Headings detected in your file:")
            st.write(list(df.columns))

            missing = [col for col in required if col not in df.columns]

            if missing:
                st.error("Some required headings are still missing:")
                st.write(missing)
                st.info(
                    "Check the detected headings above. "
                    "If all headings appear in one column, "
                    "the CSV separator may be incorrect."
                )
            else:
                st.session_state["questions"] = df
                st.success(f"Loaded {len(df)} questions successfully!")
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Could not read the CSV file: {e}")

elif page == "Mock Test":
    st.header("Mock Test")

    if "questions" not in st.session_state:
        st.info("First open Upload Questions and load your CSV.")
    else:
        df = st.session_state["questions"]

        exams = sorted(df["exam"].dropna().unique())
        selected_exam = st.selectbox("Choose exam", exams)
        test_df = df[df["exam"] == selected_exam].reset_index(drop=True)

        if len(test_df) > 0:
            if "test_index" not in st.session_state:
                st.session_state["test_index"] = 0

            if "test_answers" not in st.session_state:
                st.session_state["test_answers"] = {}

            if st.session_state.get("active_exam") != selected_exam:
                st.session_state["active_exam"] = selected_exam
                st.session_state["test_index"] = 0
                st.session_state["test_answers"] = {}

            i = st.session_state["test_index"]
            i = min(i, len(test_df) - 1)
            q = test_df.iloc[i]

            st.write(f"Question {i + 1} of {len(test_df)}")
            st.subheader(str(q["question"]))

            options = {
                "A": str(q["A"]),
                "B": str(q["B"]),
                "C": str(q["C"]),
                "D": str(q["D"])
            }

            previous = st.session_state["test_answers"].get(i)
            choice = st.radio(
                "Select one answer",
                list(options.keys()),
                format_func=lambda key: f"{key}. {options[key]}",
                index=list(options.keys()).index(previous)
                if previous in options else None,
                key=f"answer_{selected_exam}_{i}"
            )

            if st.button("Check Answer"):
                if choice is None:
                    st.warning("Please select an answer.")
                else:
                    correct = str(q["answer"]).strip().upper()
                    if choice == correct:
                        st.success("Correct!")
                    else:
                        st.error(f"Incorrect. Correct answer: {correct}")
                    st.write("Explanation:", q["explanation"])
                    st.session_state["test_answers"][i] = choice

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Previous", disabled=(i == 0)):
                    st.session_state["test_index"] = i - 1
                    st.rerun()

            with col2:
                if st.button(
                    "Next",
                    disabled=(i == len(test_df) - 1)
                ):
                    st.session_state["test_index"] = i + 1
                    st.rerun()

            st.caption(
                f"Answered: {len(st.session_state['test_answers'])}"
                f" / {len(test_df)}"
            )


elif page == "Flashcards":
    import random

    st.title("My Flashcards")
    st.write("Upload questions and answers, then revise them.")

    uploaded_file = st.file_uploader(
        "Upload Flashcards CSV",
        type=["csv"],
        key="flashcards_upload"
    )

    if uploaded_file is not None:
        try:
            df_cards = pd.read_csv(
                uploaded_file,
                encoding="utf-8-sig"
            )

            df_cards.columns = (
                df_cards.columns.str.strip().str.lower()
            )

            if not {"front", "back"}.issubset(df_cards.columns):
                st.error(
                    "CSV must contain these headings: front, back"
                )
            else:
                df_cards = df_cards.dropna(
                    subset=["front", "back"]
                ).reset_index(drop=True)

                st.session_state["flashcard_data"] = (
                    df_cards[["front", "back"]].astype(str)
                )

                if (
                    "flashcard_order" not in st.session_state
                    or len(st.session_state["flashcard_order"])
                    != len(df_cards)
                ):
                    st.session_state["flashcard_order"] = list(
                        range(len(df_cards))
                    )
                    st.session_state["flashcard_index"] = 0

        except Exception as e:
            st.error(f"Could not read CSV: {e}")

    if "flashcard_data" in st.session_state:
        cards = st.session_state["flashcard_data"]

        if len(cards) == 0:
            st.warning("Your CSV contains no flashcards.")
        else:
            if "flashcard_order" not in st.session_state:
                st.session_state["flashcard_order"] = list(
                    range(len(cards))
                )
                st.session_state["flashcard_index"] = 0

            if "flashcard_known" not in st.session_state:
                st.session_state["flashcard_known"] = set()

            if "flashcard_review" not in st.session_state:
                st.session_state["flashcard_review"] = set()

            if "flashcard_revealed" not in st.session_state:
                st.session_state["flashcard_revealed"] = False

            order = st.session_state["flashcard_order"]
            index = st.session_state["flashcard_index"]
            index = index % len(order)
            st.session_state["flashcard_index"] = index

            card_id = order[index]
            front = cards.iloc[card_id]["front"]
            back = cards.iloc[card_id]["back"]

            st.write(
                f"Card {index + 1} of {len(order)}"
            )

            st.progress((index + 1) / len(order))

            st.subheader("Question — Front")
            st.info(front)

            if st.button(
                "Show Answer",
                key="show_flashcard_answer"
            ):
                st.session_state["flashcard_revealed"] = True

            if st.session_state["flashcard_revealed"]:
                st.subheader("Answer — Back")
                st.success(back)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✓ I Know It", key="card_known"):
                        st.session_state["flashcard_known"].add(
                            card_id
                        )
                        st.session_state["flashcard_review"].discard(
                            card_id
                        )
                        st.session_state["flashcard_index"] = (
                            (index + 1) % len(order)
                        )
                        st.session_state["flashcard_revealed"] = False
                        st.rerun()

                with col2:
                    if st.button("× Need Review", key="card_review"):
                        st.session_state["flashcard_review"].add(
                            card_id
                        )
                        st.session_state["flashcard_known"].discard(
                            card_id
                        )
                        st.session_state["flashcard_index"] = (
                            (index + 1) % len(order)
                        )
                        st.session_state["flashcard_revealed"] = False
                        st.rerun()

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Previous"):
                    st.session_state["flashcard_index"] = (
                        index - 1
                    ) % len(order)
                    st.session_state["flashcard_revealed"] = False
                    st.rerun()

            with col2:
                if st.button("Next"):
                    st.session_state["flashcard_index"] = (
                        index + 1
                    ) % len(order)
                    st.session_state["flashcard_revealed"] = False
                    st.rerun()

            with col3:
                if st.button("Shuffle Cards"):
                    new_order = order.copy()
                    random.shuffle(new_order)
                    st.session_state["flashcard_order"] = new_order
                    st.session_state["flashcard_index"] = 0
                    st.session_state["flashcard_revealed"] = False
                    st.rerun()

            st.divider()
            st.subheader("Revision Progress")
            st.metric(
                "Cards known",
                len(st.session_state["flashcard_known"])
            )
            st.metric(
                "Cards to review",
                len(st.session_state["flashcard_review"])
            )
            
