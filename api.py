from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from rembg import remove
from PIL import Image
from pathlib import Path
import shutil
import os
import secrets
from jinja2 import Environment, DictLoader

# --- TEMPLATE DEFINITION (Updated index.html content) ---
INDEX_TEMPLATE_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Background Eraser</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            /* Lighter, more modern background */
            background-color: #f7f9fb; 
        }
        /* Custom checkerboard pattern for transparent background visibility */
        .checkerboard {
            background-image: linear-gradient(45deg, #ccc 25%, transparent 25%), 
                              linear-gradient(-45deg, #ccc 25%, transparent 25%),
                              linear-gradient(45deg, transparent 75%, #ccc 75%),
                              linear-gradient(-45deg, transparent 75%, #ccc 75%);
            background-size: 20px 20px;
            background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
        }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">

    <div class="w-full max-w-5xl bg-white shadow-2xl shadow-indigo-200/50 rounded-2xl p-10 space-y-10">
        <header class="text-center">
            <h1 class="text-4xl font-extrabold text-gray-900 mb-3 tracking-tight">✨ AI Background Eraser ✨</h1>
            <p class="text-xl text-gray-600 mb-4">Instantly remove the background from any image with powerful AI.</p>
            <p class="text-sm font-medium text-indigo-600">Created by <span class="font-bold">Tech Titans</span></p>
        </header>

        <hr class="border-t border-gray-200">

        {% if error_message %}
        <div class="bg-red-50 border-l-4 border-red-500 text-red-800 p-4 rounded-lg" role="alert">
            <p class="font-bold">Processing Error</p>
            <p>{{ error_message }}</p>
        </div>
        {% endif %}

        <div class="grid lg:grid-cols-2 gap-10">
            
            <div class="border border-indigo-200 p-8 rounded-xl bg-indigo-50 flex flex-col justify-center transition-all duration-300 hover:shadow-lg">
                <h2 class="text-2xl font-bold text-gray-800 mb-6 flex items-center space-x-2">
                    <svg class="w-6 h-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                    <span>1. Upload Image</span>
                </h2>
                <form action="/" method="post" enctype="multipart/form-data" class="space-y-6">
                    
                    <label class="block">
                        <span class="sr-only">Choose file</span>
                        <input type="file" name="photo" accept="image/*" required 
                                class="block w-full text-lg text-gray-700
                                file:mr-4 file:py-3 file:px-6
                                file:rounded-full file:border-0
                                file:text-base file:font-semibold
                                file:bg-indigo-600 file:text-white
                                hover:file:bg-indigo-700
                                transition duration-200 ease-in-out
                                cursor-pointer"
                        />
                    </label>

                    <button type="submit" 
                            class="w-full px-4 py-3 bg-indigo-500 text-white text-lg font-extrabold rounded-xl shadow-lg shadow-indigo-500/30 hover:bg-indigo-600 focus:outline-none focus:ring-4 focus:ring-indigo-300 transition duration-150 ease-in-out disabled:opacity-50 transform hover:scale-[1.01]"
                            id="process-button"
                    >
                        🚀 Process & Remove Background
                    </button>
                </form>
            </div>

            <div class="flex flex-col items-center justify-center space-y-6 bg-gray-50 p-8 rounded-xl border border-gray-200 shadow-inner">
                <h2 class="text-2xl font-bold text-gray-800 flex items-center space-x-2">
                    <svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <span>2. Result</span>
                </h2>
                {% if output_image_url %}
                    <div class="w-full h-64 flex items-center justify-center p-2 rounded-lg checkerboard shadow-md">
                        <img src="{{ output_image_url }}" alt="Image with Background Removed" 
                             class="max-w-full max-h-full object-contain bg-white border-2 border-green-500 rounded-lg"
                             style="image-rendering: -webkit-optimize-contrast;"
                        >
                    </div>
                    
                    <a href="{{ output_image_url }}" download="ai_bg_eraser_result.png"
                       class="mt-4 px-8 py-3 bg-green-500 text-white text-lg font-bold rounded-full shadow-xl shadow-green-500/30 hover:bg-green-600 transition duration-200 ease-in-out flex items-center space-x-2 transform hover:scale-105"
                    >
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        <span>Download PNG</span>
                    </a>
                {% else %}
                    <div class="text-center text-gray-500 p-8">
                        <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                        <p class="text-lg font-medium">Your processed image will appear here.</p>
                        <p class="text-sm mt-1">Supports PNG, JPG, and more!</p>
                    </div>
                {% endif %}
            </div>

        </div>
        
        <hr class="border-t border-gray-200">
        <footer class="text-center text-sm text-gray-500 pt-4">
             Powered by FastAPI and rembg.
        </footer>
    </div>

</body>
</html>
"""

# --- FASTAPI SETUP ---
app = FastAPI()

UPLOAD_FOLDER = "uploads"
# Use Pathlib for robust path management
UPLOAD_PATH = Path(UPLOAD_FOLDER)
UPLOAD_PATH.mkdir(exist_ok=True)

# Mount the uploads directory to be served statically
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

# Set up Jinja2 Environment to load template from the string
env = Environment(loader=DictLoader({"index.html": INDEX_TEMPLATE_CONTENT}))
template = env.get_template("index.html")

# Helper function for secure filename generation
def secure_filename(filename: str) -> str:
    """Generates a secure and unique filename."""
    name, ext = os.path.splitext(filename)
    if not name:
        return ""
    token = secrets.token_hex(8)
    # Simple sanitization, prioritizing security over preserving original name fully
    sanitized_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).strip()
    return f"{sanitized_name}_{token}{ext.lower()}" # Ensure lowercase extension


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serves the main image upload form."""
    rendered_html = template.render(
        request=request, 
        output_image_url=None, 
        error_message=None
    )
    return HTMLResponse(content=rendered_html)

@app.post("/", response_class=HTMLResponse)
async def post_index(request: Request, photo: UploadFile = File(...)):
    """Handles file upload and background removal processing."""
    error_message = None
    output_image_url = None
    
    # 1. Secure filename generation
    filename = secure_filename(photo.filename)
    if not filename:
        error_message = "Invalid file name."
        rendered_html = template.render(request=request, output_image_url=None, error_message=error_message)
        return HTMLResponse(content=rendered_html)
        
    input_path = UPLOAD_PATH / filename
    output_path = None # Initialize outside try/finally
    
    try:
        # 2. Save the uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
            
        # 3. Process the image (remove background)
        input_image = Image.open(input_path)
        output_image = remove(input_image)
        
        # 4. Define output filename and path (always save as PNG for transparency)
        base_name = input_path.stem
        output_filename = f"no_bg_{base_name}.png"
        output_path = UPLOAD_PATH / output_filename
        
        # 5. Save the output image
        output_image.save(output_path, format="PNG")
        
        # 6. Generate URL for display
        output_image_url = app.url_path_for("uploads", path=output_filename)
        
    except Exception as e:
        error_message = f"Processing error: {str(e)}. Please ensure the uploaded file is a valid image (e.g., JPG, PNG)."
        # Clean up the output file if it was partially created
        if output_path and output_path.exists():
             os.remove(output_path)
             
    finally:
        # 7. Clean up the input file
        if input_path.exists():
            os.remove(input_path)
            
    # 8. Render the response HTML
    rendered_html = template.render(
        request=request,
        output_image_url=output_image_url,
        error_message=error_message,
    )
    return HTMLResponse(content=rendered_html)

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Allows the user to download the processed file."""
    file_path = UPLOAD_PATH / filename
    
    # Security check: ensure file exists and is a processed output (starts with "no_bg_")
    if file_path.is_file() and filename.startswith("no_bg_"):
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="image/png" # Set correct media type for PNG
        )
    else:
        # Attempt to delete the file if it shouldn't be served
        if file_path.is_file():
            os.remove(file_path)
        raise HTTPException(status_code=404, detail="File not found or unauthorized for download")
