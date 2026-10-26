import streamlit as st
import pandas as pd

st.set_page_config(page_title="My Exam Preparation", layout="wide")

st.title("📚 My Exam Preparation")
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


elif page == "Upload Questions":
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
            
