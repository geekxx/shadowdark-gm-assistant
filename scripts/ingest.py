
import os, glob, pandas as pd
from pypdf import PdfReader
from sqlmodel import create_engine, Session
from core.agents.rag_librarian import ingest_text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/shadowdark")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def read_markdown(path): 
    with open(path, 'r', encoding='utf-8') as f: 
        return f.read()

def read_pdf(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def read_csv(path):
    return pd.read_csv(path)

def main(input_dir):
    md_paths = glob.glob(os.path.join(input_dir, '**/*.md'), recursive=True)
    pdf_paths = glob.glob(os.path.join(input_dir, '**/*.pdf'), recursive=True)
    csv_paths = glob.glob(os.path.join(input_dir, '**/*.csv'), recursive=True)

    count = 0
    with Session(engine) as sess:
        for p in md_paths:
            text = read_markdown(p)
            ingest_text(sess, text, title=os.path.basename(p), source_id=p, doctype='note')
            count += 1
        for p in pdf_paths:
            text = read_pdf(p)
            ingest_text(sess, text, title=os.path.basename(p), source_id=p, doctype='pdf')
            count += 1
        for p in csv_paths:
            df = read_csv(p)
            text = df.to_csv(index=False)
            ingest_text(sess, text, title=os.path.basename(p), source_id=p, doctype='csv')
            count += 1
    print(f"Ingested {count} documents.")

if __name__ == '__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else '.')
