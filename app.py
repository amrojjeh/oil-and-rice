from uuid import uuid4
import json
import os
from openai import OpenAI
from flask import Flask, abort, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import tiktoken
from pdf2image import convert_from_path
import PyPDF2
import pytesseract

app = Flask(__name__)

with open("token.txt", "r") as f:
    api_key = f.read().strip()

client = OpenAI(
    api_key = api_key,
)

MAX_TOKENS = 7800
tokenizer = tiktoken.encoding_for_model("gpt-4")

def new_well():
    return {
        "name": "Default well",
        "assets": []
    }

def read_wells():
    wells = {}
    for well_filename in os.listdir("wells"):
        with open(f"wells/{well_filename}", "r") as well_file:
            well_route = well_filename.removesuffix(".json")
            wells[well_route] = json.loads(well_file.read())
            wells[well_route]["route"] = well_route
    return wells

@app.route("/")
def index():
    return redirect("/well/default")

@app.route("/well/<name>")
def well(name):
    if not os.path.isfile(f"wells/{name}.json"):
        if name == "default":
            with open("wells/default.json", "w+") as f:
                f.write(json.dumps(new_well()))
        else:
            abort(404)
    wells = read_wells()
    selected = wells[name]
    timeline = None
    if len(selected["assets"]) != 0:
        timeline = getChatAnswer(map(lambda x: x["id"], selected["assets"]))
    return render_template("index.html", wells=wells, selected=selected, timeline=timeline)

@app.route("/well/<name>/add-pdf", methods=["GET", "POST"])
def add_pdf(name):
    if request.method == "GET":
        wells = read_wells()
        selected = wells[name]
        return render_template("add_pdf.html", selected=selected)
    for file in request.files.getlist("file"):
        file_id = uuid4()
        file.save(f"uploads/{secure_filename(str(file_id))}.pdf")
        # Assume well exists
        data = None
        with open(f"wells/{name}.json", "r") as well_file:
            data = json.loads(well_file.read())
        with open(f"wells/{name}.json", "w") as well_file:
            data["assets"].append({"name": file.filename, "id": str(file_id)})
            well_file.write(json.dumps(data))
    return redirect(url_for("index"))

def send_to_openai_api(text_content):
    """
    Sends the extracted text to OpenAI's GPT-4 API and gets a response.
    """
    if not text_content.strip():
        print("No content to send to OpenAI API.")
        return None

    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user","content":"This is a part of the information of a well you will receive, please tell me the dates and events that are important to the lifecycle of the well based on all the information. Please answer it in json. Please only answer the json file and if you can't find anything related, please just answer zero."},
                {
                    "role": "user",
                    "content": text_content
                }
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def extract_text_from_pdfs(pdfs):
    """
    Extracts text from all PDF files in a folder using PyPDF2 and falls back to OCR if no text is extracted.
    """
    all_text = ""

    for pdf in pdfs:
        file_path = os.path.join("uploads", pdf + ".pdf")

        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)

            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text = page.extract_text()

                # If no text is extracted, attempt OCR
                if not text:
                    images = convert_from_path(file_path, first_page=page_num + 1, last_page=page_num + 1)
                    for image in images:
                        text = pytesseract.image_to_string(image)

                if text:
                    all_text += text + "\n"

    return all_text


def split_text_into_chunks(text, max_tokens):
    """
    Splits the text into chunks that do not exceed the max token limit.
    """
    tokens = tokenizer.encode(text)
    chunks = []

    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.decode(chunk_tokens)
        chunks.append(chunk_text)

    return chunks

def final_question(sum_response):
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant who has been provided with detailed information."},
                {"role": "user", "content": "Could you summarize the dates and events that are important to the lifecycle of the well based on all the information. Please answer in json "},
                {
                    "role": "user",
                    "content": sum_response
                }
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def getChatAnswer(pdfs):
    # Extract text from PDFs
    pdf_text_content = extract_text_from_pdfs(pdfs)

    # Count the tokens in the extracted text
    total_tokens = len(tokenizer.encode(pdf_text_content))

    # Split the text into chunks, with a max of MAX_TOKENS tokens per chunk
    text_chunks = split_text_into_chunks(pdf_text_content, MAX_TOKENS)

    sum_response=""
    # Send each chunk to the OpenAI API and collect responses
    for i, chunk in enumerate(text_chunks):
        response = send_to_openai_api(chunk)

        # Print the response for each chunk
        if response:
            sum_response = sum_response + response + "\n"

    final_response=final_question(sum_response)
    return final_response
