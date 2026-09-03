import nbformat
from nbclient import NotebookClient

print("Starting headless notebook execution of src/02_analyse.ipynb...")
with open("src/02_analyse.ipynb") as f:
    nb = nbformat.read(f, as_version=4)

client = NotebookClient(nb, timeout=600, kernel_name="python3")
client.execute()

with open("src/02_analyse.ipynb", "w", encoding="utf-8") as f:
    nbformat.write(nb, f)

print("Notebook execution completed successfully and saved with outputs!")
