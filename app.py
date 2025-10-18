
import pytesseract
from PIL import Image

# Set the path to your Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load a sample image (replace with a real image path)
image_path = r'C:\Users\tbenics\OneDrive - Itron\Desktop\Hit_\Hit__0.png'
image = Image.open(image_path)

# Run OCR
text = pytesseract.image_to_string(image)

# Print the result
print("Extracted Text:")
print(text)
