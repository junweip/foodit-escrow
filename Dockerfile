# 1. Base Image (Official Python Slim)
FROM python:3.11-slim

# 2. Set Environment Variables
ENV PYTHONUNBUFFERED=1

# 3. Work Directory
WORKDIR /code

# 4. Install Dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. Copy Source Code
COPY ./app /code/app

# 6. Run the Application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
