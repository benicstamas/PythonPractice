# Copilot Instructions for PythonPractice

## Project Overview
This workspace contains standalone Python utility scripts for data processing and IoT messaging. No unified application architecture - each script operates independently.

## Dependencies & Setup
Install required packages:
```bash
pip install pillow pandas pytesseract meshtastic cbor2
```

For OCR functionality (`app.py`):
- Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
- Update `pytesseract.pytesseract.tesseract_cmd` path in `app.py`

For Meshtastic messaging (`MeshtasticTXStream`):
- Install Meshtastic CLI: `pip install meshtastic`
- Ensure Meshtastic device is connected and configured

## Running Scripts
Execute scripts directly with Python:
```bash
python app.py                    # OCR images to CSV
python pandatest.py              # Test pandas DataFrame
python MeshtasticTXStream        # Send timed messages via Meshtastic
python Cborconvert <input_dir> <output.csv>  # Convert CBOR files to CSV
```

## Code Patterns
- **Data Processing**: Use pandas DataFrames for CSV output (see `app.py`, `Cborconvert`)
- **External Tools**: Call via subprocess with error handling and retries (see `MeshtasticTXStream`)
- **Image Handling**: PIL for loading, pytesseract for OCR (see `app.py`)
- **CBOR Decoding**: cbor2 for SenML data flattening to tabular format (see `Cborconvert`)
- **Configuration**: Hardcode paths and settings at script top (e.g., `tesseract_cmd`, `interval_seconds`)

## File Structure
- `app.py`: OCR processing pipeline
- `pandatest.py`: Pandas basics example
- `MeshtasticTXStream`: IoT messaging script
- `Cborconvert`: SenML CBOR to CSV converter
- `ocr_results.csv`: Generated OCR output

## Development Notes
- Scripts are self-contained with minimal error handling
- Output files generated in workspace root
- No tests or build process - run scripts manually
- Update hardcoded paths for your environment</content>
<parameter name="filePath">c:\Users\tbenics\OneDrive - Itron\Desktop\PythonPractice\.github\copilot-instructions.md