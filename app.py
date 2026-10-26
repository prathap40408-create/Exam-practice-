
import os
import json
import random
import streamlit as st
import pandas as pd
from pypdf import PdfReader
from openai import OpenAI

st.set_page_config(
    page_title="Competitive Exam Study Tool",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Competitive Exam Study Tool")

# API key: Streamlit Secrets first, environment variable second
try:
    API_KEY = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
    API_KEY = ""

API_KEY = API_KEY or os.getenv("OPENAI_API_KEY", "")

if API_KEY:
    client = OpenAI(api_key=API_KEY)
else:
    client = None

if "mcqs" not in st.session_state:
    st.session_state.mcqs = []

if "flashcards" not in st.session_state:
    st.session_state.flashcards = []

if "test_answers" not in st.session_state:
    st.session_state.test_answers = {}

if "test_submitted" not in st.session_state:
    st.session_state.test_submitted = False

# ---------------- PDF FUNCTIONS ----------------

def extract_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(
                f"[PDF page {page_number}]\n{text}"
            )

    return "\n\n".join(pages)


def split_text(text, max_chars=7000):
    """Split PDF text without cutting it at arbitrary word boundaries."""
    paragraphs = text.splitlines()
    chunks = []
    current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(current) + len(paragraph) + 1 > max_chars:
            if current:
                chunks.append(current)
            current = paragraph
        else:
            current += "\n" + paragraph

    if current:
        chunks.append(current)

    return chunks


def ask_ai(prompt):
    if not client:
        raise ValueError(
            "Add your OPENAI_API_KEY in Streamlit Secrets first."
        )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert competitive-exam question setter. "
                    "Create accurate SSC CPO, SSC CGL and RRB NTPC-level "
                    "study material. Use only facts supported by the "
                    "provided PDF text. Never invent facts, answers, dates, "
                    "articles or explanations. Avoid childish questions, "
                    "trivial sentence blanks and duplicate questions. "
                    "Return valid JSON only."
                )
            },
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    return json.loads(response.choices[0].message.content)


def generate_mcqs(pdf_text, wanted=120):
    chunks = split_text(pdf_text)
    if not chunks:
        return []

    results = []
    seen = set()

    # Generate in small batches to handle large PDFs.
    # Multiple rounds help when a PDF has only a few text chunks.
    for round_number in range(4):
        for chunk_number, chunk in enumerate(chunks):
            remaining = wanted - len(results)
            if remaining <= 0:
                break

            batch_size = min(10, remaining)
            existing = [q["question"] for q in results]

            prompt = f"""
Create exactly {batch_size} distinct competitive-exam MCQs
from the SOURCE TEXT below.

Return this JSON structure:
{{
  "questions": [
    {{
      "question": "Clear exam-level question",
      "options": {{
        "A": "Option A",
        "B": "Option B",
        "C": "Option C",
        "D": "Option D"
      }},
      "answer": "C",
      "explanation": "Short, accurate explanation supported by the source"
    }}
  ]
}}

Rules:
- Four options, exactly one correct answer.
- Include important facts, concepts, dates, people, places,
  definitions, comparisons and cause-and-effect relationships
  where the source supports them.
- Wrong options must be plausible but clearly incorrect.
- Do not turn random sentences into fill-in-the-blank questions.
- Do not repeat these existing questions:
{json.dumps(existing[-100:], ensure_ascii=False)}
- If the source cannot support more distinct, accurate questions,
  return only the questions it can support.
- Do not use outside facts.
- The explanation must be supported by the source.

SOURCE TEXT:
{chunk}
"""

            try:
                data = ask_ai(prompt)
                for item in data.get("questions", []):
                    question = item.get("question", "").strip()
                    options = item.get("options", {})
                    answer = str(item.get("answer", "")).strip().upper()
                    explanation = item.get("explanation", "").strip()

                    if (
                        not question
                        or not isinstance(options, dict)
                        or set(options.keys()) != {"A", "B", "C", "D"}
                        or answer not in {"A", "B", "C", "D"}
                        or not explanation
                    ):
                        continue

                    key = question.casefold()
                    if key in seen:
                        continue

                    seen.add(key)
                    results.append({
                        "question": question,
                        "options": options,
                        "answer": answer,
                        "explanation": explanation
                    })

                    if len(results) >= wanted:
                        break

            except Exception as error:
                st.warning(
                    f"Could not process PDF section "
                    f"{chunk_number + 1}: {error}"
                )

        if len(results) >= wanted:
            break

    return results[:wanted]


def generate_flashcards(pdf_text, wanted=40):
    chunks = split_text(pdf_text)
    cards = []
    seen = set()

    for chunk_number, chunk in enumerate(chunks):
        if len(cards) >= wanted:
            break

        batch_size = min(10, wanted - len(cards))

        prompt = f"""
Create up to {batch_size} useful competitive-exam flashcards
from the SOURCE TEXT.

Return JSON:
{{
  "flashcards": [
    {{
      "front": "One clear question",
      "back": "Exact answer plus a short supporting explanation"
    }}
  ]
}}

Rules:
- Front must contain a question or clear recall prompt.
- Back must give the answer, not another question.
- Cover important facts and concepts suitable for SSC CPO,
  SSC CGL and RRB NTPC.
- No childish questions, random blanks or duplicate cards.
- Do not invent facts or use outside knowledge.
- If the source cannot support more useful cards, return fewer.

SOURCE TEXT:
{chunk}
"""
        try:
            data = ask_ai(prompt)
            for item in data.get("flashcards", []):
                front = item.get("front", "").strip()
                back = item.get("back", "").strip()

                if not front or not back:
                    continue

                key = front.casefold()
                if key in seen:
                    continue

                seen.add(key)
                cards.append({"front": front, "back": back})

                if len(cards) >= wanted:
                    break

        except Exception as error:
            st.warning(
                f"Could not process flashcard section "
                f"{chunk_number + 1}: {error}"
            )

    return cards[:wanted]


# ---------------- MENU ----------------

page = st.sidebar.radio(
    "Choose a page",
    ["Home", "PDF to MCQ", "Mock Test", "Flashcards"]
)

if page == "Home":
    st.header("Welcome")
    st.write(
        "Upload your study PDF to create exam-level MCQs "
        "and question-answer flashcards."
    )
    st.write("**Target exams:** SSC CPO, SSC CGL, RRB NTPC and more.")
    st.info(
        "Generated questions are based on the extracted PDF text. "
        "Scanned PDFs may need OCR before their text can be read."
    )

# ---------------- PDF TO MCQ ----------------

elif page == "PDF to MCQ":
    st.header("PDF to Competitive-Exam MCQs")

    pdf_file = st.file_uploader(
        "Upload your study PDF",
        type=["pdf"],
        key="mcq_pdf"
    )

    if pdf_file:
        st.caption(f"Uploaded: {pdf_file.name}")

        if st.button("Generate 120 MCQs", type="primary"):
            try:
                with st.spinner(
                    "Reading the PDF and generating questions..."
                ):
                    pdf_text = extract_pdf(pdf_file)

                    if len(pdf_text.strip()) < 100:
                        st.error(
                            "Very little text was extracted. "
                            "This may be a scanned PDF; OCR may be needed."
                        )
                    else:
                        st.session_state.mcqs = generate_mcqs(
                            pdf_text, 120
                        )
                        st.session_state.test_answers = {}
                        st.session_state.test_submitted = False

            except Exception as error:
                st.error(f"Could not read PDF: {error}")

    if st.session_state.mcqs:
        st.success(
            f"{len(st.session_state.mcqs)} MCQs generated."
        )

        if len(st.session_state.mcqs) < 120:
            st.warning(
                "Fewer than 120 questions were generated. "
                "Check the extracted PDF text and API results. "
                "Do not assume the PDF lacks information."
            )

        for i, q in enumerate(st.session_state.mcqs, start=1):
            with st.expander(f"Question {i}: {q['question']}"):
                st.write(f"A) {q['options']['A']}")
                st.write(f"B) {q['options']['B']}")
                st.write(f"C) {q['options']['C']}")
                st.write(f"D) {q['options']['D']}")
                st.write(f"**Correct answer:** {q['answer']}) "
                         f"{q['options'][q['answer']]}")
                st.write(f"**Explanation:** {q['explanation']}")

        mcq_export = []
        for i, q in enumerate(st.session_state.mcqs, start=1):
            mcq_export.append({
                "No.": i,
                "Question": q["question"],
                "Option A": q["options"]["A"],
                "Option B": q["options"]["B"],
                "Option C": q["options"]["C"],
                "Option D": q["options"]["D"],
                "Correct Answer": q["answer"],
                "Explanation": q["explanation"]
            })

        csv_data = pd.DataFrame(mcq_export).to_csv(index=False)
        st.download_button(
            "Download MCQs as CSV",
            data=csv_data,
            file_name="competitive_exam_mcqs.csv",
            mime="text/csv"
        )

# ---------------- MOCK TEST ----------------

elif page == "Mock Test":
    st.header("Mock Test")
    st.write("Scoring: +1 correct, −0.33 incorrect, 0 unanswered.")

    questions = st.session_state.mcqs

    if not questions:
        st.info(
            "First generate MCQs from your PDF in the PDF to MCQ page."
        )
    else:
        if st.button("Start / Reset Mock Test"):
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False

        for i, q in enumerate(questions):
            choice = st.radio(
                f"Q{i + 1}. {q['question']}",
                options=["Not answered", "A", "B", "C", "D"],
                format_func=lambda x, q=q: (
                    x if x == "Not answered"
                    else f"{x}) {q['options'][x]}"
                ),
                key=f"test_{i}",
                index=0
            )
            if choice == "Not answered":
                st.session_state.test_answers.pop(i, None)
            else:
                st.session_state.test_answers[i] = choice

        if st.button("Submit Mock Test", type="primary"):
            st.session_state.test_submitted = True

        if st.session_state.test_submitted:
            correct = 0
            wrong = 0
            unanswered = 0

            for i, q in enumerate(questions):
                answer = st.session_state.test_answers.get(i)

                if answer is None:
                    unanswered += 1
                elif answer == q["answer"]:
                    correct += 1
                else:
                    wrong += 1

            score = correct - (wrong * 0.33)
            attempted = correct + wrong
            accuracy = (
                correct / attempted * 100 if attempted else 0
            )

            st.subheader("Your Result")
            st.metric("Score", f"{score:.2f} / {len(questions)}")
            st.write(f"Correct: {correct}")
            st.write(f"Incorrect: {wrong}")
            st.write(f"Unanswered: {unanswered}")
            st.write(f"Accuracy of attempted questions: {accuracy:.2f}%")

            st.subheader("Answer Analysis")
            for i, q in enumerate(questions):
                chosen = st.session_state.test_answers.get(i)
                st.write(f"**Q{i + 1}. {q['question']}**")
                st.write(
                    f"Your answer: {chosen or 'Not answered'}"
                )
                st.write(
                    f"Correct answer: {q['answer']}) "
                    f"{q['options'][q['answer']]}"
                )
                st.write(f"Explanation: {q['explanation']}")

# ---------------- FLASHCARDS ----------------

elif page == "Flashcards":
    st.header("PDF-Based Flashcards")

    pdf_file = st.file_uploader(
        "Upload your study PDF",
        type=["pdf"],
        key="flashcard_pdf"
    )

    card_count = st.selectbox(
        "Number of flashcards",
        [10, 20, 30, 40],
        index=3
    )

    if pdf_file and st.button("Generate Flashcards", type="primary"):
        try:
            with st.spinner("Creating question-answer flashcards..."):
                pdf_text = extract_pdf(pdf_file)

                if len(pdf_text.strip()) < 100:
                    st.error(
                        "Very little text was extracted. "
                        "This PDF may need OCR."
                    )
                else:
                    st.session_state.flashcards = generate_flashcards(
                        pdf_text, card_count
                    )
        except Exception as error:
            st.error(f"Could not read PDF: {error}")

    if st.session_state.flashcards:
        st.success(
            f"{len(st.session_state.flashcards)} flashcards generated."
        )

        for i, card in enumerate(
            st.session_state.flashcards, start=1
        ):
            with st.expander(f"Card {i}: {card['front']}"):
                st.markdown("**FRONT — QUESTION**")
                st.write(card["front"])
                st.divider()
                st.markdown("**BACK — ANSWER**")
                st.write(card["back"])

        card_data = pd.DataFrame(st.session_state.flashcards)
        st.download_button(
            "Download Flashcards as CSV",
            data=card_data.to_csv(index=False),
            file_name="competitive_exam_flashcards.csv",
            mime="text/csv"
            )
    
