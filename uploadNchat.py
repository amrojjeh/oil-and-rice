import os
import PyPDF2
from openai import OpenAI
from pdf2image import convert_from_path
import pytesseract
import tiktoken  # Import tiktoken for accurate token counting

client = OpenAI(
    api_key = "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",
)

# Define the maximum token limit per request
MAX_TOKENS = 7800

# Initialize tokenizer (using GPT-4 tokenizer)
tokenizer = tiktoken.encoding_for_model("gpt-4")


def extract_text_from_pdfs(folder_path):
    """
    Extracts text from all PDF files in a folder using PyPDF2 and falls back to OCR if no text is extracted.
    """
    all_text = ""

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)

            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)

                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    text = page.extract_text()

                    # If no text is extracted, attempt OCR
                    if not text:
                        print(f"No text extracted from {filename}, page {page_num + 1}, attempting OCR...")
                        images = convert_from_path(file_path, first_page=page_num + 1, last_page=page_num + 1)
                        for image in images:
                            text = pytesseract.image_to_string(image)

                    if text:
                        all_text += text + "\n"
                    else:
                        print(f"OCR failed to extract text from {filename}, page {page_num + 1}")

    return all_text


def save_text_to_file(text, output_file):
    """
    Saves the extracted text to a file.
    """
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(text)


def read_text_from_file(file_path):
    """
    Reads the text from a file.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def count_tokens(text):
    """
    Counts the number of tokens in the text using tiktoken.
    """
    return len(tokenizer.encode(text))


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


def getChatAnswer(folder_path,output_file):

    # Extract text from PDFs
    extracted_text = extract_text_from_pdfs(folder_path)

    # Save the extracted text to a file
    save_text_to_file(extracted_text, output_file)
    print(f"Text has been saved to {output_file}")

    # Read the text back from the file
    pdf_text_content = read_text_from_file(output_file)

    # Count the tokens in the extracted text
    total_tokens = count_tokens(pdf_text_content)
    print(f"Total tokens in text: {total_tokens}")

    # Split the text into chunks, with a max of MAX_TOKENS tokens per chunk
    text_chunks = split_text_into_chunks(pdf_text_content, MAX_TOKENS)
    print(f"Text has been split into {len(text_chunks)} chunks.")

    sum_response=""
    # Send each chunk to the OpenAI API and collect responses
    for i, chunk in enumerate(text_chunks):
        print(f"Processing chunk {i + 1}/{len(text_chunks)}...")
        response = send_to_openai_api(chunk)

        # Print the response for each chunk
        if response:
            print(f"Response for chunk {i + 1}:{response}")
            sum_response = sum_response + response + "\n"
        else:
            print(f"No valid response received for chunk {i + 1}.")

    with open("testing_response.txt", "w", encoding="utf-8") as file:
        file.write(sum_response)
    final_response=final_question(sum_response)
    if final_response:
        print("Final response based on all chunks:")
        print(final_response)
    else:
        print("No valid final response received.")


getChatAnswer("/Users/hl19/Desktop/challenge2/Well_4249534691","/Users/hl19/Desktop/challenge2/Well_4249534691/Result.txt")