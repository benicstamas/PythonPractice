import os
import re
import pytesseract
from PIL import Image
import pandas as pd

# Set path to Tesseract executable (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Folder containing your images
image_folder = r'C:\Users\tbenics\OneDrive - Itron\Pictures'

# Output CSV file
output_csv = 'ocr_results.csv'

# Regex patterns to extract key values

# Store results
results = []

# Process each image
for filename in os.listdir(image_folder):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(image_folder, filename)
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)

        results.append(text)

# Save to CSV
df = pd.DataFrame(results)
df.to_csv(output_csv, index=False)
print(f"OCR results saved to {output_csv}")